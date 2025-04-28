import pandas as pd
import numpy as np
from scipy.signal import find_peaks, sosfiltfilt, iirfilter
from fitting import  DipModel, ComposedDipModel, ColeModel, DoubleColeModel, LorentzianModel, ColeLorentzianModel, SOC_RISC_Model, LorentzianNonLorentzianModel, NonLorentzianModel, DoubleLorentzianModel, DoubleNonLorentzianModel, LorentzianColeModel

import os
import logging
import plotly.graph_objects as go
import yaml

# Processing constants
SAMPLING_RATE: float = 833
DEFAULT_FILTER_ORDER: int = 5
DEFAULT_FILTER_CUTOFF: int = 40
DEFAULT_FILTER_TYPE: str = "lowpass"
B_FIELD_RANGE = (-192, 192)

# Peak detection constants
PEAK_WIDTH = 1000
PEAK_DISTANCE = 1000

# Fitting constants
TAU_RANGE_START = -3
TAU_RANGE_END = 3
TAU_POINTS = 10000

# Config file
CONFIG_FILE = "process_config.yaml"

if not __name__ == "__main__":
    logger = logging.getLogger(__name__)


def create_dir(path: str, name: str) -> str:
    output_path = f"{path}/{name}"
    print(output_path)
    if not os.path.isdir(output_path):
        os.mkdir(output_path)
    return output_path


def get_split_points_by_extrema(df):
    pos_peaks = find_peaks(df["B"], width=PEAK_WIDTH, distance=PEAK_DISTANCE)
    neg_peaks = find_peaks(df["B"] * -1, width=PEAK_WIDTH, distance=PEAK_DISTANCE)
    peaks = np.append(pos_peaks[0], neg_peaks[0])
    peaks.sort()
    return peaks


def get_split_points_channel(df):
    channel_idx = df.index[df["Channel"] != df["Channel"].shift()]
    return channel_idx


def get_split_points_temp(df):
    temp_idx = df.index[df["Temp"] != df["Temp"].shift()]
    return temp_idx


def get_change_points(df: pd.DataFrame, columns: list[str] | str) -> pd.Index:
    """
    Identify indices where any of the specified columns have a change in value.

    Parameters:
        df (pd.DataFrame): The input DataFrame.
        columns (str or list[str]): A single column name or a list of column names to check for changes.

    Returns:
        pd.Index: Combined and sorted indices where changes occur in any column.
    """
    if isinstance(columns, str):
        columns = [columns]
    change_indices = set()  # Use a set to avoid duplicates
    for column in columns:
        change_indices.update(df.index[df[column] != df[column].shift()])
    return pd.Index(sorted(change_indices))


def add_ramp_idx(df: pd.DataFrame, splits: list[int]):
    def get_ramp_idx(index):
        for i, val in enumerate(splits):
            if index < val:
                return i
        return len(splits)

    df["ramp_idx"] = df.index.map(get_ramp_idx)


def split_df(df: pd.DataFrame, splits: list[int] | pd.Index) -> list[pd.DataFrame]:
    dfs = []
    start = 0
    for end in splits:
        split = df.iloc[start:end].copy()
        dfs.append(split.reset_index())
        start = end
    last_split = df.loc[splits[-1] :].copy()
    dfs.append(last_split.reset_index())
    return dfs


def get_best_model(x, y, models: list[DipModel], score="cp"):
    best_model = None
    best_score = None
    for model in models:
        if not model.fitted:
            logger.warning(f"{model}: not fitted")
            continue
        r2, rmse, mae, aic, bic, cp, adjusted_r2 = model.evaluate(x_data=x, true_y=y)
        logger.debug(
            f"{model}: r2={r2:.3f}, rmse={rmse:.3f}, mae={mae:.3f}, aic={aic:.3f}, bic={bic:.3f}, cp={cp:.3f}, adjusted_r2={adjusted_r2:.3f}"
        )
        if score == "r2":
            if not best_score or best_score < r2:
                best_model = model
                best_score = r2
        elif score == "rmse":
            if not best_score or best_score > rmse:
                best_model = model
                best_score = rmse
        elif score == "mae":
            if not best_score or best_score > mae:
                best_model = model
                best_score = mae
        elif score == "aic":
            if not best_score or best_score > aic:
                best_model = model
                best_score = aic
        elif score == "bic":
            if not best_score or best_score > bic:
                best_model = model
                best_score = bic
        elif score == "cp":
            if not best_score or best_score > cp:
                best_model = model
                best_score = bic
        elif score == "adjusted_r2":
            if not best_score or best_score < adjusted_r2:
                best_model = model
                best_score = adjusted_r2

        else:
            raise NotImplementedError
    return best_model, best_score


def preprocess_ramp(ramp: pd.DataFrame, config: dict):
    # support legacy code with 'I_OLED' column
    if "I_OLED" in ramp:
        ramp["OLED"] = ramp["I_OLED"]
        ramp = ramp.drop("I_OLED")
    ramp = (
        ramp.pipe(
            filter_ramp,
            column="OLED",
            new_column_name="oled_filtered",
            **config["ramp"]["oled"]["filter"],
        )
        .pipe(
            filter_ramp,
            column="I_Photo",
            new_column_name="photo_filtered",
            **config["ramp"]["photo"]["filter"],
        )
        .pipe(center_dip, column="photo_filtered")
        .pipe(center_dip, column="oled_filtered")
        .dropna()
        .pipe(calc_relative_change, column='oled_filtered', new_column_name='omc')
        .pipe(calc_relative_change, column='photo_filtered', new_column_name='mel')
        .query(f"B >= {B_FIELD_RANGE[0]} and B<= {B_FIELD_RANGE[1]}")
        .pipe(subtract_linear_trend, column='omc')
        .pipe(subtract_linear_trend, column='mel')
        .pipe(add_magnetoefficiency, mode=config["measurement"]["OLED"]["power_type"])
    )

    return ramp


def fit_models(x_data, y_data, models_to_use: list[str]):
    models: list[DipModel] = [
        ColeModel(),
        DoubleColeModel(),
        ColeLorentzianModel(),
        NonLorentzianModel(),
        DoubleNonLorentzianModel(),
        LorentzianModel(),
        DoubleLorentzianModel(),
        LorentzianNonLorentzianModel(), 
        LorentzianColeModel(), 
        SOC_RISC_Model()
    ]
    #   Only keep models which are in the config
    if models_to_use is not None:
        logger.info(f"models to use: {models_to_use}")
        models = [model for model in models if model.name in models_to_use]
    for model in models:
        model.fit(x_data=x_data, y_data=y_data)
        logger.info(f"{model} is fitted: {model.fitted}")
    return models


def add_model_predictions(
    ramp: pd.DataFrame, model: DipModel | ComposedDipModel, new_column_name: str
):
    if not model:
        return ramp
    if isinstance(model, ComposedDipModel):
        for component_name, function in model.get_fitted_component_functions().items():
            ramp[f"{new_column_name}_{component_name}"] = np.array(
                [function(x) for x in ramp["B"]]
            )
    ramp[new_column_name] = model.predict(ramp["B"])
    return ramp


def add_magnetoefficiency(
    ramp: pd.DataFrame, mode='V', new_column_name: str = "mageff_detrend"
) -> pd.DataFrame:
    if mode == 'V':
        ramp[new_column_name] = ramp["mel_detrend"] - ramp["omc_detrend"]
    if mode == 'I':
        ramp[new_column_name] = ramp["mel_detrend"] + ramp["omc_detrend"]
    return ramp


def subtract_linear_trend(
    ramp: pd.DataFrame, column: str, new_column_name: str | None = None
) -> pd.DataFrame:
    if not new_column_name:
        new_column_name = column + "_detrend"
    ramp = ramp.sort_values("B")
    slope_mel = (ramp[column].iat[-1] - ramp[column].iat[0]) / (
        ramp["B"].iat[-1] - ramp["B"].iat[0]
    )
    ramp[new_column_name] = ramp[column] - slope_mel * ramp["B"]
    return ramp


def calc_relative_change(
    ramp: pd.DataFrame, column: str, new_column_name: str | None = None
) -> pd.DataFrame:
    if not new_column_name:
        new_column_name = column + "_rel_change"
    B_at_zero_idx = ramp["B"].abs().idxmin()
    base_line = ramp.loc[B_at_zero_idx, column]
    ramp[new_column_name] = 100 * (ramp[column] - base_line) / abs(base_line)
    return ramp


def center_dip(
    ramp: pd.DataFrame, dip_search_range: float = 5, column: str = "photo_filtered"
) -> pd.DataFrame:
    B_at_zero_idx = ramp["B"].abs().idxmin()
    low_vals = ramp.loc[ramp["B"].abs() < dip_search_range, column]
    if len(low_vals) == 0:
        logger.error(f"No values found in ramp with B < {dip_search_range}")
        return ramp
    val_at_edge = ramp.iloc[(ramp["B"] - dip_search_range).abs().argsort()[0]][column]
    if val_at_edge < ramp[column].iat[B_at_zero_idx]:
        photo_extrem_idx = low_vals.idxmax()
    else:
        photo_extrem_idx = low_vals.idxmin()
    shift_ammount = B_at_zero_idx - photo_extrem_idx
    ramp[column] = ramp[column].shift(shift_ammount)
    return ramp


def filter_ramp(
    df: pd.DataFrame,
    column: str,
    N: int = DEFAULT_FILTER_ORDER,
    Wn: int = DEFAULT_FILTER_CUTOFF,
    btype: str = DEFAULT_FILTER_TYPE,
    fs: float = SAMPLING_RATE,
    new_column_name: str | None = None,
) -> pd.DataFrame:
    """Filter ramp data using specified parameters."""
    if not new_column_name:
        new_column_name = f"{column}_filtered"
    sos = iirfilter(N=N, btype=btype, Wn=Wn, output="sos", fs=fs)
    return df.assign(**{new_column_name: sosfiltfilt(sos, df[column])})


def remove_faulty_ramps(ramps: list[pd.DataFrame]):
    #   Throw away first and last ramp. They might be not complete.
    #   Can be replaced by a more sophisticated function to remove faulty ramps.
    ramps = ramps[1:-1]
    return ramps


def ramps_from_measurement(measurement: pd.DataFrame):
    split_points = get_split_points_by_extrema(measurement)
    add_ramp_idx(measurement, split_points)
    return split_df(measurement, split_points)


def analyze_effect(ramp: pd.DataFrame, effect_name: str, config: dict, tau_range):
    fit_info = dict()
    x_data = ramp["B"]
    y_data = ramp[f'{effect_name}_detrend']
    g_data = {}
    for models_to_use, model_type in zip(config["models"], ["cole", "lorentz"]):
        logger.debug(f"models to use: {models_to_use}")
        logger.info(f"analyze {effect_name}_{model_type}")
        models = fit_models(x_data, y_data, models_to_use=models_to_use)
        best_model, best_model_score = get_best_model(
            x_data, y_data, models, score=config["fit_score"]
        )
        if best_model:
            logger.info(
                f'best model: {best_model}, best_score: ({config["fit_score"]}): {best_model_score}'
            )
            ramp = add_model_predictions(
                ramp, best_model, f"{effect_name}_fit_{model_type}"
            )
            try:
                g = best_model.get_g(tau_range)
                fit_info.update(
                    {f"max_tau_{effect_name}_{model_type}": tau_range[np.argmax(g)]}
                )
                g_data[f"g_{effect_name}_{model_type}"] = g
            except NotImplementedError as e:
                logger.error(e)
            model_params = {
                f"{name}_{effect_name}_{model_type}": param
                for name, param in zip(best_model.param_names, best_model.params)
            }
            fit_info.update(model_params)
            fit_info[f"model_{effect_name}_{model_type}"] = best_model.name
            fit_info[f'{config["fit_score"]}_{effect_name}_{model_type}'] = (
                best_model_score
            )
    return fit_info, g_data


def process_measurement(path: str, config: dict):
    logger.info(f"process measurement from {path}")
    output_path = create_dir(path, name="processed")
    measurement = pd.read_csv(f"{path}/data.csv", comment="#")
    with open(f"{path}/config.yaml", mode="r") as f:
        measurement_config = yaml.safe_load(f)
    config.update({'measurement':measurement_config})
    ramps = ramps_from_measurement(measurement)
    ramps = remove_faulty_ramps(ramps)
    fit_data = []
    for ramp in ramps:
        ramp_idx = ramp["ramp_idx"].array[0]
        logger.info(f"Ramp idx: {ramp_idx}")
        ramp_fit_data = {"ramp": ramp_idx}
        tau_range = np.logspace(TAU_RANGE_START, TAU_RANGE_END, TAU_POINTS)
        ramp_g_data = {"tau": tau_range}
        ramp = preprocess_ramp(ramp, config)
        fitting_config = config["ramp"]["fitting"]
        for effect_name in fitting_config["effects_to_fit"]:
            fit_info, g_value = analyze_effect(
                ramp,
                effect_name=effect_name,
                config=fitting_config[effect_name],
                tau_range=tau_range,
            )
            ramp_g_data.update(g_value)
            ramp_fit_data.update(fit_info)
        ramp_data = ramp.drop(columns=["V_Hall", "ramp_idx", "omc", "mel"])
        ramp_data.to_csv(f"{output_path}/measurements_{ramp_idx}.csv")
        pd.DataFrame(ramp_g_data).set_index("tau").to_csv(
            output_path + f"/normalized_g{ramp_idx}.csv"
        )
        fit_data.append(ramp_fit_data)
    pd.DataFrame(fit_data).set_index("ramp").to_csv(output_path + "/ramp_data.csv")


def process_measurement_cryo(path: str, config: dict):
    logger.info(f"process measurement from {path}")
    output_path = create_dir(path, name="processed")
    measurement = pd.read_csv(f"{path}/data.csv", comment="#")
    with open(f"{path}/config.yaml", mode="r") as f:
        measurement_config = yaml.safe_load(f)
    config.update({'measurement':measurement_config})
    channel_split_points = get_change_points(measurement, columns="Channel")
    channels = split_df(measurement, channel_split_points)
    mel_temp_dependency_dict = {}
    omc_temp_dependency_dict = {}
    for channel in channels[1:]:
        fit_data = []
        temp = channel['Temp_sample'].array[0]
        channel_idx = channel['Channel'].array[0]
        if channel_idx not in mel_temp_dependency_dict:
            mel_temp_dependency_dict[channel_idx] = {}
        if channel_idx not in omc_temp_dependency_dict:
            omc_temp_dependency_dict[channel_idx] = {}
        logger.info(f'process channel {channel_idx}')
        logger.info(f'channel_type: {type(channel)}')
        ramps = ramps_from_measurement(channel)
        ramps = remove_faulty_ramps(ramps)
        logger.info(f"process channel {channel}")
        for ramp in ramps:
            logger.info(type(ramp))
            ramp_idx = ramp["ramp_idx"].array[0]
            logger.info(f"Ramp idx: {ramp_idx}")
            ramp_fit_data = {"ramp": ramp_idx}
            tau_range = np.logspace(TAU_RANGE_START, TAU_RANGE_END, TAU_POINTS)
            ramp_g_data = {"tau": tau_range}
            ramp = preprocess_ramp(ramp, config)
            fitting_config = config["ramp"]["fitting"]
            for effect_name in effects_to_fit:
                fit_info, g_value = analyze_effect(
                    ramp,
                    effect_name=effect_name,
                    config=fitting_config[effect_name],
                    tau_range=tau_range,
                )
                ramp_g_data.update(g_value)
                ramp_fit_data.update(fit_info)
            fit_data.append(ramp_fit_data)
            ramp_data = ramp.drop(columns=['V_Hall', 'ramp_idx', 'omc', 'mel'])
            current_temp = ramp['Temp_sample'].array[0]
            if str(current_temp) not in mel_temp_dependency_dict[channel_idx]:
                mel_temp_dependency_dict[channel_idx][str(current_temp)] = []
            try:
                mel_temp_dependency_dict[channel_idx][str(current_temp)].append(ramp['mel_fit_lorentz'].iloc[0])
            except:
                continue
            if str(current_temp) not in omc_temp_dependency_dict[channel_idx]:
               omc_temp_dependency_dict[channel_idx][str(current_temp)] = []
            try:
                omc_temp_dependency_dict[channel_idx][str(current_temp)].append(ramp['omc_fit_lorentz'].iloc[0])
            except:
                continue
            logger.info(f"Ramp idx after analyze effect{ramp_idx}")
            logger.info(f"Ramp data frame length: {len(ramp_data)}")
            ramp_data.to_csv(f'{output_path}/temperature_{temp}_K_channel_{channel_idx}_measurements_{ramp_idx}.csv')
            pd.DataFrame(ramp_g_data).set_index('tau').to_csv(output_path+f'/normalized_g{ramp_idx}.csv')
        pd.DataFrame(fit_data).set_index('ramp').to_csv(output_path+f'/temperature_{temp}_K_channel_{channel_idx}_ramp_data.csv')
    
    for channel_idx, mel_temp_dict in mel_temp_dependency_dict.items():
        first_data_mel = []

        for temp, first_mels in mel_temp_dict.items():
            first_data_mel.append({'temp': temp, 'avg': np.mean(first_mels), 'std': np.std(first_mels), 'ln(MEL)': np.log(np.mean(first_mels)), 'error(ln(MEL))': (np.std(first_mels))/(np.mean(first_mels))})
        pd.DataFrame(first_data_mel).to_csv(output_path+f'/channel_{channel_idx}_temp_dependency_mel.csv')

    for channel_idx, omc_temp_dict in omc_temp_dependency_dict.items():
        first_data_omc = []

        for temp, first_omcs in omc_temp_dict.items():
            first_data_omc.append({'temp': temp, 'avg': np.mean(first_omcs), 'std': np.std(first_omcs), 'ln(OMC)': np.log(np.mean(first_omcs)), 'error(ln(OMC))': (np.std(first_omcs))/(np.mean(first_omcs))})
        pd.DataFrame(first_data_omc).to_csv(output_path+f'/channel_{channel_idx}_temp_dependency_omc.csv')

if __name__ == "__main__":
    import yaml
    from log import setup_logger

    logger = setup_logger(debug_level=logging.INFO)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, CONFIG_FILE)
    with open(config_path, mode="r") as f:
        config = yaml.safe_load(f)
    process_measurement_cryo(script_dir, config=config)
