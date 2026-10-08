FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV ANDROID_HOME=/opt/android-sdk
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$PATH:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools:/opt/gradle-8.2/bin
ENV PYTHONUNBUFFERED=1

# 1) تحديث + تثبيت Java 17 + Python + أدوات
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    python3 python3-pip \
    wget unzip curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2) تحميل Android Command-Line Tools
RUN mkdir -p $ANDROID_HOME/cmdline-tools && \
    wget -q https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip -O /tmp/cmd.zip && \
    unzip -q /tmp/cmd.zip -d $ANDROID_HOME/cmdline-tools && \
    mv $ANDROID_HOME/cmdline-tools/cmdline-tools $ANDROID_HOME/cmdline-tools/latest && \
    rm /tmp/cmd.zip

# 3) قبول التراخيص + تثبيت مكونات Android
RUN yes | sdkmanager --licenses || true
RUN sdkmanager "platforms;android-34" "build-tools;34.0.0" "platform-tools"

# 4) تحميل Gradle 8.2
RUN wget -q https://services.gradle.org/distributions/gradle-8.2-bin.zip -O /tmp/g.zip && \
    unzip -q /tmp/g.zip -d /opt && \
    rm /tmp/g.zip

# 5) المشروع
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/builds /app/keystore

CMD ["python3", "bot.py"]
