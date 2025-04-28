from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QStyle, QLabel, QHBoxLayout, \
    QWidget, QSizePolicy, QPushButton
import os


class MyBar(QWidget):
    clickPos = None

    def __init__(self, parent):
        super(MyBar, self).__init__(parent)

        # Set layout for the bar
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 4)  # Add some margins for spacing

        # Title Label
        self.title = QLabel("", self)
        self.title.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet(f"font-size: 12pt; font-weight: bold; color: {os.environ.get('QTMATERIAL_SECONDARYTEXTCOLOR')};")
        layout.addStretch(1)
        layout.addWidget(self.title)
        layout.addStretch(1)
        
        # Set the height dynamically based on the font size and buttons
        ref_size = self.fontMetrics().height() + 12
        self.setMaximumHeight(ref_size+8)

        # Button size adjustment (increase the size)
        btn_size = QSize(ref_size, ref_size)  # Increase button size to make icons larger
        for target in ('min', 'normal', 'max', 'close'):
            # Create buttons for minimize, maximize, restore, close
            btn = QPushButton(self)
            btn.setFixedSize(btn_size)
            if target == 'min':
                icon = QPixmap("assets/min.png")
                btn.setIcon(QIcon(icon))
                btn.setIconSize(QSize(16, 16))
            if target == 'max':
                icon = QPixmap("assets/max.png")
                btn.setIcon(QIcon(icon))
                btn.setIconSize(QSize(16, 16))
            if target == 'close':
                icon = QPixmap("assets/close.png")
                btn.setIcon(QIcon(icon))
                btn.setIconSize(QSize(16, 16))
                btn.setProperty("class", "danger")
            if target == 'normal':
                icon = QPixmap("assets/normal.png")
                btn.setIcon(QIcon(icon))
                btn.setIconSize(QSize(16, 16))
            layout.addWidget(btn)
            
            # Connect the button to the corresponding action
            signal = getattr(self, f'{target}Clicked')
            btn.clicked.connect(signal)
            setattr(self, f'{target}Button', btn)
        self.normalButton.hide()  # Hide normal button when window is maximized
        self.updateTitle(parent.windowTitle())
        parent.windowTitleChanged.connect(self.updateTitle)

    def updateTitle(self, title=None):
        """Update the window title with proper truncation for long titles."""
        if title is None:
            title = self.window().windowTitle()
        width = self.title.width() - self.style().pixelMetric(QStyle.PM_LayoutHorizontalSpacing) * 2
        self.title.setText(self.fontMetrics().elidedText(title, Qt.ElideRight, width))

    def mousePressEvent(self, event):
        """Handle mouse press event for dragging the window."""
        if event.button() == Qt.LeftButton:
            self.clickPos = event.windowPos().toPoint()

    def mouseMoveEvent(self, event):
        """Handle mouse move event for dragging the window."""
        if self.clickPos is not None:
            self.window().move(event.globalPos() - self.clickPos)

    def mouseReleaseEvent(self, event):
        """Reset the click position when mouse is released."""
        self.clickPos = None

    def closeClicked(self):
        """Handle close button click."""
        self.window().close()

    def maxClicked(self):
        """Handle maximize button click."""
        self.normalButton.show()
        self.maxButton.hide()
        self.window().showFullScreen()

    def normalClicked(self):
        """Handle restore button click."""
        self.normalButton.hide()
        self.maxButton.show()
        self.window().showNormal()

    def minClicked(self):
        """Handle minimize button click."""
        self.window().showMinimized()

    def resizeEvent(self, event):
        """Handle resize event for title update."""
        self.updateTitle()

