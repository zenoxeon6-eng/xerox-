FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    ANDROID_HOME=/opt/android-sdk \
    ANDROID_SDK_ROOT=/opt/android-sdk \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH=$PATH:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:/opt/gradle-8.2/bin \
    PYTHONUNBUFFERED=1

# ─── أدوات البناء ───
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jdk-headless \
    wget unzip curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ─── Android Command-Line Tools ───
RUN mkdir -p $ANDROID_HOME/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O /tmp/cmd.zip && \
    unzip -q /tmp/cmd.zip -d $ANDROID_HOME/cmdline-tools && \
    mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/latest && \
    rm /tmp/cmd.zip

# ─── قبول التراخيص وتثبيت المكونات ───
RUN yes | sdkmanager --licenses > /dev/null 2>&1 && \
    sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools" > /dev/null 2>&1

# ─── Gradle 8.2 ───
RUN wget -q https://services.gradle.org/distributions/gradle-8.2-bin.zip -O /tmp/g.zip && \
    unzip -q /tmp/g.zip -d /opt && \
    rm /tmp/g.zip

# ─── المشروع ───
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/builds /app/keystore

EXPOSE 8080

CMD ["python", "bot.py"]
