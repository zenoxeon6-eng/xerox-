FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH=/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:/opt/gradle-8.2/bin:/usr/lib/jvm/java-17-openjdk-amd64/bin:$PATH \
    PYTHONUNBUFFERED=1

# ─── 1) تثبيت Java 17 من مستودع bookworm-backports ───
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates wget unzip curl gnupg && \
    mkdir -p /usr/share/keyrings && \
    wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public \
        | gpg --dearmor -o /usr/share/keyrings/adoptium.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/adoptium.gpg] https://packages.adoptium.net/artifactory/deb bookworm main" \
        > /etc/apt/sources.list.d/adoptium.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends temurin-17-jdk && \
    rm -rf /var/lib/apt/lists/*

# ─── 2) Android Command-line Tools ───
RUN mkdir -p $ANDROID_HOME/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O /tmp/cmd.zip && \
    unzip -q /tmp/cmd.zip -d $ANDROID_HOME/cmdline-tools && \
    mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/latest && \
    rm /tmp/cmd.zip

# ─── 3) قبول التراخيص + تثبيت Android SDK ───
RUN yes | sdkmanager --licenses > /dev/null 2>&1 || true && \
    sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools" > /dev/null 2>&1

# ─── 4) Gradle 8.2 ───
RUN wget -q https://services.gradle.org/distributions/gradle-8.2-bin.zip -O /tmp/g.zip && \
    unzip -q /tmp/g.zip -d /opt && \
    rm /tmp/g.zip

# ─── 5) المشروع ───
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/builds /app/keystore

CMD ["python", "bot.py"]
