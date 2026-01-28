# ui/main_window.py
import urllib.request

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QProgressBar
)

from .worker import PresenceWorker

PRIMARY = "#7289da"
BG = "#6b7cc8"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Rich Music Presence")
        self.setFixedSize(520, 620)

        self.worker = None
        self._artwork_url = ""

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

        # Always start on connect screen for now
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

        subtitle = QLabel("Display what you're listening to on your Discord profile")
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

        self.connect_btn = QPushButton("Connect Now")
        self.connect_btn.setObjectName("CTA")
        self.connect_btn.clicked.connect(self._on_connect_clicked)

        self.connect_status = QLabel("")
        self.connect_status.setObjectName("Foot")
        self.connect_status.setAlignment(Qt.AlignCenter)
        self.connect_status.setWordWrap(True)

        foot = QLabel(
            "By connecting, you authorize Rich Music Presence to display your\n"
            "currently playing music on Discord"
        )
        foot.setObjectName("Foot2")
        foot.setAlignment(Qt.AlignCenter)
        foot.setWordWrap(True)

        v.addWidget(title)
        v.addWidget(subtitle)
        v.addWidget(features)
        v.addWidget(self.connect_btn)
        v.addWidget(self.connect_status)
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
        now.setObjectName("NowCard")
        nv = QVBoxLayout(now)
        nv.setContentsMargins(26, 24, 26, 24)
        nv.setSpacing(8)

        self.d_art = QLabel("♪")
        self.d_art.setObjectName("AlbumArtBig")
        self.d_art.setFixedSize(280, 280)
        self.d_art.setAlignment(Qt.AlignCenter)

        self.d_song = QLabel("Nothing playing")
        self.d_song.setObjectName("SongTitle")
        self.d_song.setWordWrap(True)
        self.d_song.setAlignment(Qt.AlignCenter)

        self.d_artist = QLabel("—")
        self.d_artist.setObjectName("ArtistName")
        self.d_artist.setWordWrap(True)
        self.d_artist.setAlignment(Qt.AlignCenter)

        self.d_album = QLabel("")
        self.d_album.setObjectName("AlbumName")
        self.d_album.setWordWrap(True)
        self.d_album.setAlignment(Qt.AlignCenter)

        self.d_playing_line = QLabel("")
        self.d_playing_line.setObjectName("PlayingLine")
        self.d_playing_line.setAlignment(Qt.AlignCenter)

        self.d_progress = QProgressBar()
        self.d_progress.setObjectName("TrackProgress")
        self.d_progress.setRange(0, 1000)
        self.d_progress.setValue(0)
        self.d_progress.setTextVisible(False)
        self.d_progress.setFixedHeight(8)

        time_row = QWidget()
        time_layout = QHBoxLayout(time_row)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(8)

        self.d_time_left = QLabel("0:00")
        self.d_time_left.setObjectName("TimeText")

        self.d_time_right = QLabel("0:00")
        self.d_time_right.setObjectName("TimeText")

        time_layout.addWidget(self.d_time_left, 0, Qt.AlignLeft)
        time_layout.addStretch()
        time_layout.addWidget(self.d_time_right, 0, Qt.AlignRight)

        nv.addWidget(self.d_art, 0, Qt.AlignHCenter)
        nv.addWidget(self.d_song)
        nv.addWidget(self.d_artist)
        nv.addWidget(self.d_album)
        nv.addWidget(self.d_playing_line)
        nv.addWidget(self.d_progress)
        nv.addWidget(time_row)

        layout.addWidget(account)
        layout.addWidget(now)

        footer = QLabel("Rich Music Presence")
        footer.setObjectName("FooterNote")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        return page

    # ==================================================
    # WORKER HOOKUP
    # ==================================================

    def _on_connect_clicked(self):
        self.connect_btn.setEnabled(False)
        self.connect_status.setText("Connecting…")

        self._start_worker()

        # Move to dashboard immediately (worker can update after)
        self.stack.setCurrentWidget(self.dashboard_page)

    def _start_worker(self):
        if self.worker:
            return

        self.worker = PresenceWorker(poll_seconds=3, parent=self)

        # Required signal: now_playing(dict)
        self.worker.now_playing.connect(self._on_now_playing)

        # Optional signal: status(str) — only connect if it exists
        if hasattr(self.worker, "status"):
            try:
                self.worker.status.connect(self._on_worker_status)
            except Exception:
                pass

        self.worker.start()

    def _on_worker_status(self, msg: str):
        # Show status on connect page and in dashboard status line
        self.connect_status.setText(msg)
        self.d_status.setText(msg)

    def _format_time(self, seconds: float) -> str:
        try:
            total = max(0, int(seconds))
        except Exception:
            total = 0
        mins = total // 60
        secs = total % 60
        return f"{mins}:{secs:02d}"

    def _on_now_playing(self, np: dict):
        title = (np.get("title") or "").strip()
        artist = (np.get("artist") or "").strip()
        album = (np.get("album") or "").strip()
        playing = bool(np.get("playing"))
        artwork_url = (np.get("artwork_url") or "").strip()
        duration = float(np.get("duration") or 0)
        position = float(np.get("position") or 0)

        if title:
            self.d_song.setText(title)
            self.d_artist.setText(artist or "—")
            self.d_album.setText(album or "")
            self.d_status.setText("Playing" if playing else "Paused")
        else:
            self.d_song.setText("Nothing playing")
            self.d_artist.setText("—")
            self.d_album.setText("")
            self.d_status.setText("Idle")

        if artwork_url != self._artwork_url:
            self._artwork_url = artwork_url
            self._set_artwork(artwork_url)

        if duration > 0:
            progress = max(0.0, min(1.0, position / duration))
            self.d_progress.setValue(int(progress * 1000))
        else:
            self.d_progress.setValue(0)

        if duration > 0:
            self.d_time_left.setText(self._format_time(position))
            self.d_time_right.setText(self._format_time(duration))
        else:
            self.d_time_left.setText("0:00")
            self.d_time_right.setText("0:00")

    def _set_artwork(self, url: str):
        if not url:
            self.d_art.setPixmap(QPixmap())
            self.d_art.setText("♪")
            return

        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                data = resp.read()
            pix = QPixmap()
            if pix.loadFromData(data):
                scaled = pix.scaled(
                    self.d_art.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                self.d_art.setPixmap(scaled)
                self.d_art.setText("")
                return
        except Exception:
            pass

        self.d_art.setPixmap(QPixmap())
        self.d_art.setText("♪")

    # ==================================================
    # CLEAN SHUTDOWN
    # ==================================================

    def closeEvent(self, event):
        # For now, close = quit (we’ll do tray later)
        self._stop_worker()
        event.accept()

    def _stop_worker(self):
        if not self.worker:
            return
        try:
            self.worker.stop()
        except Exception:
            pass
        self.worker = None

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
                qproperty-textInteractionFlags: NoTextInteraction;
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
                color: rgba(255,255,255,0.90);
            }}

            QLabel#Foot2 {{
                font-size: 11px;
                color: rgba(255,255,255,0.85);
            }}

            QFrame#GlassCard {{
                background-color: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 22px;
            }}

            QFrame#NowCard {{
                background-color: rgba(255,255,255,0.30);
                border: 1px solid rgba(255,255,255,0.24);
                border-radius: 26px;
            }}

            QLabel#DashTitle {{
                font-size: 18px;
                font-weight: 800;
            }}

            QLabel#DashMuted {{
                font-size: 13px;
                color: rgba(255,255,255,0.70);
            }}

            QLabel#SongTitle {{
                font-size: 18px;
                font-weight: 800;
            }}

            QLabel#ArtistName {{
                font-size: 13px;
                color: rgba(255,255,255,0.85);
            }}

            QLabel#AlbumName {{
                font-size: 12px;
                color: rgba(255,255,255,0.70);
            }}

            QLabel#StatusMuted {{
                font-size: 11px;
                color: rgba(255,255,255,0.65);
            }}

            QLabel#AlbumArtBig {{
                background-color: rgba(255,255,255,0.18);
                border-radius: 22px;
                color: rgba(255,255,255,0.85);
                font-size: 28px;
                font-weight: 800;
            }}

            QProgressBar#TrackProgress {{
                background-color: rgba(255,255,255,0.22);
                border: 0px;
                border-radius: 999px;
            }}

            QProgressBar#TrackProgress::chunk {{
                background-color: rgba(255,255,255,0.90);
                border-radius: 999px;
            }}

            QLabel#TimeText {{
                font-size: 11px;
                color: rgba(255,255,255,0.75);
                qproperty-textInteractionFlags: NoTextInteraction;
                selection-background-color: transparent;
            }}

            QLabel#FooterNote {{
                font-size: 11px;
                color: rgba(255,255,255,0.65);
            }}
        """)
