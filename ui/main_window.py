# ui/main_window.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget
)

PRIMARY = "#7289da"
BG = "#0b1020"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Rich Music Presence")
        self.setFixedSize(520, 620)

        # ================= ROOT =================
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setAlignment(Qt.AlignCenter)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()

        self.connect_page = self._build_connect_page()
        self.dashboard_page = self._build_dashboard_page()

        self.stack.addWidget(self.connect_page)
        self.stack.addWidget(self.dashboard_page)

        root_layout.addWidget(self.stack)
        self.setCentralWidget(root)

        self._apply_styles()

        # always start on connect for now
        self.stack.setCurrentWidget(self.connect_page)

    # ==================================================
    # CONNECT PAGE
    # ==================================================

    def _build_connect_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(420)

        v = QVBoxLayout(card)
        v.setSpacing(18)
        v.setContentsMargins(28, 28, 28, 28)

        title = QLabel("Connect Your Music")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(
            "Display what you're listening to on your Discord profile"
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)

        features = QFrame()
        features.setObjectName("Features")
        fv = QVBoxLayout(features)
        fv.setSpacing(10)
        fv.setContentsMargins(14, 14, 14, 14)

        fv.addWidget(self._feature("Real-time music updates"))
        fv.addWidget(self._feature("Beautiful album artwork display"))
        fv.addWidget(self._feature("Show your music taste"))

        connect_btn = QPushButton("Connect Now")
        connect_btn.setObjectName("CTA")
        connect_btn.clicked.connect(
            lambda: self.stack.setCurrentWidget(self.dashboard_page)
        )

        foot = QLabel(
            "By connecting, you authorize Rich Music Presence to display your\n"
            "currently playing music on Discord"
        )
        foot.setObjectName("Foot")
        foot.setAlignment(Qt.AlignCenter)
        foot.setWordWrap(True)

        v.addWidget(title)
        v.addWidget(subtitle)
        v.addWidget(features)
        v.addWidget(connect_btn)
        v.addWidget(foot)

        layout.addWidget(card)
        return page

    def _feature(self, text: str):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)

        dot = QLabel("•")
        dot.setObjectName("Dot")

        label = QLabel(text)
        label.setObjectName("FeatureText")

        h.addWidget(dot)
        h.addWidget(label)
        h.addStretch()
        return row

    # ==================================================
    # DASHBOARD PAGE
    # ==================================================

    def _build_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignTop)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Account card
        account = QFrame()
        account.setObjectName("GlassCard")
        av = QVBoxLayout(account)
        av.setContentsMargins(20, 18, 20, 18)
        av.setSpacing(4)

        acc_title = QLabel("Connected")
        acc_title.setObjectName("DashTitle")

        acc_sub = QLabel("Discord account")
        acc_sub.setObjectName("DashMuted")

        av.addWidget(acc_title)
        av.addWidget(acc_sub)

        # Now Playing card
        now = QFrame()
        now.setObjectName("GlassCard")
        nv = QVBoxLayout(now)
        nv.setContentsMargins(20, 18, 20, 18)
        nv.setSpacing(6)

        song = QLabel("Nothing playing")
        song.setObjectName("Song")

        artist = QLabel("—")
        artist.setObjectName("DashMuted")

        status = QLabel("Idle")
        status.setObjectName("Status")

        nv.addWidget(song)
        nv.addWidget(artist)
        nv.addWidget(status)

        layout.addWidget(account)
        layout.addWidget(now)

        return page

    # ==================================================
    # STYLES (NO HIGHLIGHTS)
    # ==================================================

    def _apply_styles(self):
        self.setStyleSheet(f"""
            * {{
                background: transparent;
                outline: none;
                selection-background-color: transparent;
                selection-color: white;
            }}

            QWidget {{
                background-color: {BG};
                color: white;
                font-family: -apple-system, BlinkMacSystemFont,
                             "Segoe UI", Inter, Arial;
            }}

            QLabel {{
                background: transparent;
            }}

            QFrame#Card {{
                background-color: {PRIMARY};
                border-radius: 24px;
            }}

            QLabel#Title {{
                font-size: 22px;
                font-weight: 800;
            }}

            QLabel#Subtitle {{
                font-size: 14px;
                color: rgba(255,255,255,0.9);
            }}

            QFrame#Features {{
                background-color: rgba(255,255,255,0.12);
                border-radius: 16px;
            }}

            QLabel#Dot {{
                font-size: 18px;
                font-weight: 900;
            }}

            QLabel#FeatureText {{
                font-size: 14px;
            }}

            QPushButton#CTA {{
                background-color: white;
                color: {PRIMARY};
                border-radius: 16px;
                padding: 14px;
                font-size: 15px;
                font-weight: 800;
            }}

            QPushButton#CTA:hover {{
                background-color: #f0f0f0;
            }}

            QLabel#Foot {{
                font-size: 11px;
                color: rgba(255,255,255,0.85);
            }}

            QFrame#GlassCard {{
                background-color: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 22px;
            }}

            QLabel#DashTitle {{
                font-size: 18px;
                font-weight: 800;
            }}

            QLabel#DashMuted {{
                font-size: 13px;
                color: rgba(255,255,255,0.70);
            }}

            QLabel#Song {{
                font-size: 20px;
                font-weight: 900;
            }}

            QLabel#Status {{
                font-size: 12px;
                color: rgba(255,255,255,0.60);
            }}
        """)
