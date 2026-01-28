# ui/main_window.py
import math
import random
import urllib.request
from pathlib import Path

from PySide6.QtCore import Qt, QEasingCurve, QPoint, QPointF, QPropertyAnimation, QParallelAnimationGroup, QSequentialAnimationGroup
from PySide6.QtGui import QGuiApplication
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QProgressBar,
    QGraphicsBlurEffect, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
    QMenu, QSystemTrayIcon
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
        self._artwork_pixmap = None
        self._animating = False
        self._page_anim = None
        self._glow_effect = None
        self._glow_anim = None
        self._glow_transition = None
        self._active_poll_seconds = 1
        self._inactive_poll_seconds = 5
        self._current_poll_seconds = self._active_poll_seconds
        self._last_song_sig = None
        self._bg_anim = None
        self._bg_margin = 36
        self._bg_move = 24
        self._tray = None
        self._icon = self._load_app_icon()
        self._force_quit = False

        root = QWidget()
        root.setObjectName("Root")
        root_layout = QVBoxLayout(root)
        root_layout.setAlignment(Qt.AlignCenter)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.bg_label = QLabel(root)
        self.bg_label.setObjectName("BgArt")
        self.bg_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.bg_label.setVisible(False)

        self.stack = QStackedWidget()

        self.connect_page = self._build_connect_page()
        self.dashboard_page = self._build_dashboard_page()

        self.stack.addWidget(self.connect_page)
        self.stack.addWidget(self.dashboard_page)

        root_layout.addWidget(self.stack)
        self.setCentralWidget(root)

        self._update_background_geometry()
        self.bg_label.lower()
        self.stack.raise_()

        self._apply_styles()

        self._fade_in_root()

        self._init_tray()
        if self._icon:
            self.setWindowIcon(self._icon)

        # Always start on connect screen for now
        self.stack.setCurrentWidget(self.connect_page)

        app = QGuiApplication.instance()
        if app:
            app.applicationStateChanged.connect(self._on_app_state_changed)

    # ==================================================
    # CONNECT PAGE
    # ==================================================

    def _build_connect_page(self):
        page = QWidget()
        page.setObjectName("ConnectPage")
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
        page.setObjectName("DashboardPage")
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
        self.now_card = now
        now.setObjectName("NowCard")
        nv = QVBoxLayout(now)
        nv.setContentsMargins(26, 24, 26, 24)
        nv.setSpacing(8)

        self.d_art = QLabel("♪")
        self.d_art.setObjectName("AlbumArtBig")
        self.d_art.setFixedSize(220, 220)
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

        version = QLabel("v1.1.0")
        version.setObjectName("FooterVersion")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        return page

    # ==================================================
    # WORKER HOOKUP
    # ==================================================

    def _on_connect_clicked(self):
        self.connect_btn.setEnabled(False)
        self.connect_status.setText("Connecting…")

        self._start_worker()

        # Move to dashboard immediately (worker can update after)
        self._switch_page(self.dashboard_page)

    def _start_worker(self):
        if self.worker:
            return

        self.worker = PresenceWorker(poll_seconds=self._current_poll_seconds, parent=self)

        # Required signal: now_playing(dict)
        self.worker.now_playing.connect(self._on_now_playing)

        # Optional signal: status(str) — only connect if it exists
        if hasattr(self.worker, "status"):
            try:
                self.worker.status.connect(self._on_worker_status)
            except Exception:
                pass

        self.worker.start()

    def _on_app_state_changed(self, state):
        if state == Qt.ApplicationActive:
            if self.isHidden():
                self._show_from_tray()
            self._set_poll_seconds(self._active_poll_seconds)
        else:
            self._set_poll_seconds(self._inactive_poll_seconds)

    def _set_poll_seconds(self, seconds: int):
        self._current_poll_seconds = seconds
        if self.worker:
            self.worker.poll_seconds = seconds

    def _on_worker_status(self, msg: str):
        # Show status on connect page and in dashboard status line
        self.connect_status.setText(msg)

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
        sig = (title, artist, album)

        if title:
            self.d_song.setText(title)
            self.d_artist.setText(artist or "—")
            self.d_album.setText(album or "")
            if artist:
                self.d_playing_line.setText(
                    f"{'Playing' if playing else 'Paused'}: {title} — {artist}"
                )
            else:
                self.d_playing_line.setText(
                    f"{'Playing' if playing else 'Paused'}: {title}"
                )
        else:
            self.d_song.setText("Nothing playing")
            self.d_artist.setText("—")
            self.d_album.setText("")
            self.d_playing_line.setText("Idle")
            self._last_song_sig = None

        if artwork_url != self._artwork_url:
            self._artwork_url = artwork_url
            self._set_artwork(artwork_url)

        if sig != self._last_song_sig and title:
            self._last_song_sig = sig
            self._start_bg_motion()

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

        self._set_playing_glow(playing)

    def _set_artwork(self, url: str):
        if not url:
            self.d_art.setPixmap(QPixmap())
            self.d_art.setText("♪")
            self._artwork_pixmap = None
            self._clear_background()
            return

        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                data = resp.read()
            pix = QPixmap()
            if pix.loadFromData(data):
                self._artwork_pixmap = pix
                scaled = pix.scaled(
                    self.d_art.size(),
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                rounded = self._rounded_pixmap(scaled, radius=22)
                self.d_art.setPixmap(rounded)
                self.d_art.setText("")
                self._set_background_pixmap(pix)
                return
        except Exception:
            pass

        self.d_art.setPixmap(QPixmap())
        self.d_art.setText("♪")
        self._artwork_pixmap = None
        self._clear_background()

    def _set_background_pixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            self._clear_background()
            return

        self._update_background_geometry()
        target_size = self.bg_label.size()

        scaled = pixmap.scaled(
            target_size,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )

        composed = QPixmap(target_size)
        composed.fill(Qt.transparent)
        painter = QPainter(composed)
        painter.setOpacity(0.35)

        x = (target_size.width() - scaled.width()) // 2
        y = (target_size.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

        self.bg_label.setPixmap(composed)
        self.bg_label.setVisible(True)

        if not isinstance(self.bg_label.graphicsEffect(), QGraphicsBlurEffect):
            blur = QGraphicsBlurEffect(self.bg_label)
            blur.setBlurRadius(60)
            self.bg_label.setGraphicsEffect(blur)

    def _clear_background(self):
        if self._bg_anim:
            self._bg_anim.stop()
            self._bg_anim = None
        self.bg_label.setPixmap(QPixmap())
        self.bg_label.setVisible(False)
        self.bg_label.setGraphicsEffect(None)

    def _update_background_geometry(self):
        w = self.width()
        h = self.height()
        margin = self._bg_margin
        self.bg_label.setGeometry(-margin, -margin, w + margin * 2, h + margin * 2)

    def _start_bg_motion(self):
        if not self.bg_label.isVisible():
            return

        if self._bg_anim:
            self._bg_anim.stop()
            self._bg_anim = None

        dx = random.uniform(-1.0, 1.0)
        dy = random.uniform(-1.0, 1.0)
        length = math.hypot(dx, dy)
        if length == 0:
            dx, dy = 1.0, 0.0
            length = 1.0
        dx /= length
        dy /= length

        move = self._bg_move
        base = QPoint(-self._bg_margin, -self._bg_margin)
        delta = QPoint(int(dx * move), int(dy * move))
        start = base - delta
        end = base + delta

        forward = QPropertyAnimation(self.bg_label, b"pos")
        forward.setDuration(14000)
        forward.setStartValue(start)
        forward.setEndValue(end)
        forward.setEasingCurve(QEasingCurve.InOutSine)

        backward = QPropertyAnimation(self.bg_label, b"pos")
        backward.setDuration(14000)
        backward.setStartValue(end)
        backward.setEndValue(start)
        backward.setEasingCurve(QEasingCurve.InOutSine)

        group = QSequentialAnimationGroup(self)
        group.addAnimation(forward)
        group.addAnimation(backward)
        group.setLoopCount(-1)
        self._bg_anim = group
        group.start()

    def _set_playing_glow(self, playing: bool):
        if not self.now_card:
            return

        if not self._glow_effect:
            effect = QGraphicsDropShadowEffect(self.now_card)
            effect.setBlurRadius(14)
            effect.setOffset(QPointF(0.0, 0.0))
            effect.setColor(QColor(255, 255, 255, 40))
            self._glow_effect = effect
            self.now_card.setGraphicsEffect(effect)

        # Stop motion while transitioning states
        if self._glow_anim:
            self._glow_anim.stop()
            self._glow_anim = None

        if self._glow_transition:
            self._glow_transition.stop()
            self._glow_transition = None

        if playing:
            target_blur = 42
            target_color = QColor(255, 255, 255, 130)
        else:
            target_blur = 14
            target_color = QColor(255, 255, 255, 40)

        blur_anim = QPropertyAnimation(self._glow_effect, b"blurRadius")
        blur_anim.setDuration(320)
        blur_anim.setEndValue(target_blur)
        blur_anim.setEasingCurve(QEasingCurve.OutCubic)

        color_anim = QPropertyAnimation(self._glow_effect, b"color")
        color_anim.setDuration(320)
        color_anim.setEndValue(target_color)
        color_anim.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(blur_anim)
        group.addAnimation(color_anim)

        def _maybe_start_motion():
            if not playing:
                return
            # Subtle glow movement around the card by animating shadow offset.
            offsets = [
                QPointF(0.0, 3.0),
                QPointF(3.0, 0.0),
                QPointF(0.0, -3.0),
                QPointF(-3.0, 0.0),
            ]
            motion = QSequentialAnimationGroup(self)
            for point in offsets:
                anim = QPropertyAnimation(self._glow_effect, b"offset")
                anim.setDuration(700)
                anim.setEndValue(point)
                anim.setEasingCurve(QEasingCurve.InOutSine)
                motion.addAnimation(anim)
            motion.setLoopCount(-1)
            self._glow_anim = motion
            motion.start()

        group.finished.connect(_maybe_start_motion)
        self._glow_transition = group
        group.start()

    # ==================================================
    # PAGE TRANSITIONS
    # ==================================================

    def _switch_page(self, target: QWidget):
        if self._animating:
            return

        current = self.stack.currentWidget()
        if current is target:
            return

        self._animating = True
        w = self.stack.width()
        h = self.stack.height()

        target.setGeometry(0, 0, w, h)
        target.show()
        target.raise_()

        current_effect = QGraphicsOpacityEffect(current)
        target_effect = QGraphicsOpacityEffect(target)
        current.setGraphicsEffect(current_effect)
        target.setGraphicsEffect(target_effect)
        target_effect.setOpacity(0.0)

        duration = 260
        ease = QEasingCurve.OutCubic

        anim_current_pos = QPropertyAnimation(current, b"pos")
        anim_current_pos.setDuration(duration)
        anim_current_pos.setStartValue(current.pos())
        anim_current_pos.setEndValue(current.pos() + QPoint(0, 12))
        anim_current_pos.setEasingCurve(ease)

        anim_target_pos = QPropertyAnimation(target, b"pos")
        anim_target_pos.setDuration(duration)
        anim_target_pos.setStartValue(target.pos() + QPoint(0, 12))
        anim_target_pos.setEndValue(target.pos())
        anim_target_pos.setEasingCurve(ease)

        anim_current_op = QPropertyAnimation(current_effect, b"opacity")
        anim_current_op.setDuration(duration)
        anim_current_op.setStartValue(1.0)
        anim_current_op.setEndValue(0.0)
        anim_current_op.setEasingCurve(ease)

        anim_target_op = QPropertyAnimation(target_effect, b"opacity")
        anim_target_op.setDuration(duration)
        anim_target_op.setStartValue(0.0)
        anim_target_op.setEndValue(1.0)
        anim_target_op.setEasingCurve(ease)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_current_pos)
        group.addAnimation(anim_target_pos)
        group.addAnimation(anim_current_op)
        group.addAnimation(anim_target_op)

        def _finish():
            self.stack.setCurrentWidget(target)
            current.hide()
            current.setGraphicsEffect(None)
            target.setGraphicsEffect(None)
            current.move(0, 0)
            target.move(0, 0)
            self._animating = False
            self._page_anim = None

        group.finished.connect(_finish)
        self._page_anim = group
        group.start()

    def _fade_in_root(self):
        effect = QGraphicsOpacityEffect(self.stack)
        self.stack.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        start_pos = self.stack.pos() + QPoint(0, 10)
        end_pos = self.stack.pos()
        self.stack.move(start_pos)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(420)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        move = QPropertyAnimation(self.stack, b"pos")
        move.setDuration(420)
        move.setStartValue(start_pos)
        move.setEndValue(end_pos)
        move.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim)
        group.addAnimation(move)
        group.start()

        def _finish():
            self.stack.setGraphicsEffect(None)
            self.stack.move(end_pos)

        group.finished.connect(_finish)
        # Keep a ref so GC doesn't stop the animation
        self._root_fade = group

    def _rounded_pixmap(self, pixmap: QPixmap, radius: int) -> QPixmap:
        size = self.d_art.size()
        rounded = QPixmap(size)
        rounded.fill(Qt.transparent)

        painter = QPainter(rounded)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        path = QPainterPath()
        path.addRoundedRect(0, 0, size.width(), size.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        return rounded

    # ==================================================
    # CLEAN SHUTDOWN
    # ==================================================

    def closeEvent(self, event):
        # Minimize to tray if available
        if self._tray and self._tray.isVisible() and not self._force_quit:
            self.hide()
            event.ignore()
            return

        self._stop_worker()
        event.accept()

    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        tray = QSystemTrayIcon(self)
        tray.setToolTip("Rich Music Presence")
        if self._icon:
            tray.setIcon(self._icon)

        menu = QMenu()
        action_show = menu.addAction("Show")
        action_quit = menu.addAction("Quit")

        action_show.triggered.connect(self._show_from_tray)
        action_quit.triggered.connect(self._quit_from_tray)
        tray.activated.connect(self._on_tray_activated)

        tray.setContextMenu(menu)
        tray.show()
        self._tray = tray

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()
        if self._icon:
            self.setWindowIcon(self._icon)

    def _quit_from_tray(self):
        self._force_quit = True
        self._stop_worker()
        app = QGuiApplication.instance()
        if app:
            app.quit()
        else:
            self.close()

    def _load_app_icon(self):
        icon_path = Path(__file__).resolve().parents[1] / "logo.png"
        if icon_path.exists():
            return QIcon(str(icon_path))
        return None

    def _stop_worker(self):
        if not self.worker:
            return
        try:
            self.worker.stop()
        except Exception:
            pass
        try:
            if self.worker.isRunning():
                self.worker.quit()
                self.worker.wait(2000)
        except Exception:
            pass
        self._set_playing_glow(False)
        self._clear_background()
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
                color: white;
                font-family: -apple-system, BlinkMacSystemFont,
                             "Segoe UI", Inter, Arial;
            }}

            QMainWindow {{
                background-color: {BG};
            }}

            QWidget#Root {{
                background-color: {BG};
            }}

            QStackedWidget, QWidget#ConnectPage, QWidget#DashboardPage {{
                background: transparent;
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
                background-color: rgba(255,255,255,0.26);
                border: 1px solid rgba(255,255,255,0.24);
                border-radius: 32px;
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
                font-size: 20px;
                font-weight: 900;
            }}

            QLabel#ArtistName {{
                font-size: 14px;
                color: rgba(255,255,255,0.90);
            }}

            QLabel#AlbumName {{
                font-size: 12px;
                color: rgba(255,255,255,0.75);
            }}

            QLabel#PlayingLine {{
                font-size: 12px;
                color: rgba(255,255,255,0.70);
                border-radius: 5px;
            }}

            QLabel#AlbumArtBig {{
                background-color: rgba(255,255,255,0.16);
                border-radius: 20px;
                color: rgba(255,255,255,0.85);
                font-size: 28px;
                font-weight: 800;
            }}

            QProgressBar#TrackProgress {{
                background-color: rgba(255,255,255,0.22);
                border: 0px;
                border-radius: 5px;
            }}

            QProgressBar#TrackProgress::chunk {{
                background-color: rgba(255,255,255,0.90);
                border-radius: 5px;
            }}

            QLabel#TimeText {{
                font-size: 11px;
                color: rgba(255,255,255,0.75);
                qproperty-textInteractionFlags: NoTextInteraction;
                selection-background-color: transparent;
            }}

            QLabel#FooterNote {{
                font-size: 11px;
                color: rgba(255,255,255,0.70);
            }}

            QLabel#FooterVersion {{
                font-size: 10px;
                color: rgba(255,255,255,0.55);
            }}
        """)
