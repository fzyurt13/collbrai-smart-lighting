package com.collbrai.meraled;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothManager;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothGatt;
import android.bluetooth.BluetoothGattCallback;
import android.bluetooth.BluetoothGattCharacteristic;
import android.bluetooth.BluetoothGattDescriptor;
import android.bluetooth.BluetoothGattService;
import android.bluetooth.BluetoothProfile;
import android.bluetooth.le.BluetoothLeScanner;
import android.bluetooth.le.ScanCallback;
import android.bluetooth.le.ScanResult;
import android.bluetooth.le.ScanSettings;
import android.content.Context;
import android.content.pm.PackageManager;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.text.InputType;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.UUID;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class MainActivity extends Activity {

    private BluetoothAdapter bluetoothAdapter;
    private BluetoothLeScanner bleScanner;
    private WifiManager wifiManager;

    private WebView webView;
    private BluetoothDevice foundDevice;
    private BluetoothGatt bluetoothGatt;
    private BluetoothGattCharacteristic authCharacteristic;
    private BluetoothGattCharacteristic sessionCharacteristic;
    private BluetoothGattCharacteristic wifiSsidCharacteristic;
    private BluetoothGattCharacteristic wifiPasswordCharacteristic;
    private BluetoothGattCharacteristic wifiCommandCharacteristic;
    private BluetoothGattCharacteristic wifiStatusCharacteristic;

    private TextView statusText;
    private TextView deviceText;
    private Button scanButton;
    private Button connectButton;
    private EditText setupPinInput;

    private LinearLayout wifiSetupSection;
    private EditText wifiSsidInput;
    private EditText wifiPasswordInput;
    private Button wifiConnectButton;

    private LinearLayout wifiNetworkList;
    private TextView wifiNetworkStatusText;
    private TextView wifiSelectedNetworkText;
    private Button wifiRescanButton;
    private Button wifiManualButton;

    private LinearLayout setupStepBle;
    private LinearLayout setupStepWifi;
    private LinearLayout setupStepComplete;

    private TextView wizardStepDeviceCircle;
    private TextView wizardStepWifiCircle;
    private TextView wizardStepCompleteCircle;

    private TextView wizardStepDeviceLabel;
    private TextView wizardStepWifiLabel;
    private TextView wizardStepCompleteLabel;

    private View wizardStepLineOne;
    private View wizardStepLineTwo;

    private TextView completeSummaryText;

    private Button bleNextButton;
    private Button wifiBackButton;
    private Button wifiNextButton;
    private Button completeBackButton;
    private Button finishSetupButton;

    private final Handler handler = new Handler();

    private String foundDeviceName = null;
    private String pendingSetupPin = null;

    private String pendingWifiSsid = null;
    private String pendingWifiPassword = null;

    private boolean setupSessionActive = false;
    private boolean setupWifiConnected = false;
    private boolean wifiScanAttempted = false;

    private String selectedWifiSsid = null;

    private String setupWifiSsid = null;
    private String setupWifiIp = null;

    private static final int BLE_PERMISSION_REQUEST = 1001;
    private static final int WIFI_PERMISSION_REQUEST = 1002;

    private static final String NEARBY_WIFI_DEVICES_PERMISSION =
        "android.permission.NEARBY_WIFI_DEVICES";

    private static final long SCAN_PERIOD_MS = 10000;

    private static final String MERALED_MAIN_URL =
        "http://192.168.1.27:8080/";

    private static final String BLUETOOTH_SCAN_PERMISSION =
        "android.permission.BLUETOOTH_SCAN";

    private static final String BLUETOOTH_CONNECT_PERMISSION =
        "android.permission.BLUETOOTH_CONNECT";

    private static final UUID MERALED_SERVICE_UUID =
        UUID.fromString(
            "8f7a0001-4c5d-4f31-8e6d-158298000001"
        );

    private static final UUID AUTH_UUID =
        UUID.fromString(
            "8f7a0004-4c5d-4f31-8e6d-158298000001"
        );

    private static final UUID SESSION_UUID =
        UUID.fromString(
            "8f7a0003-4c5d-4f31-8e6d-158298000001"
        );

    private static final UUID WIFI_SSID_UUID =
        UUID.fromString(
            "8f7a0005-4c5d-4f31-8e6d-158298000001"
        );

    private static final UUID WIFI_PASSWORD_UUID =
        UUID.fromString(
            "8f7a0006-4c5d-4f31-8e6d-158298000001"
        );

    private static final UUID WIFI_COMMAND_UUID =
        UUID.fromString(
            "8f7a0007-4c5d-4f31-8e6d-158298000001"
        );

    private static final UUID WIFI_STATUS_UUID =
        UUID.fromString(
            "8f7a0008-4c5d-4f31-8e6d-158298000001"
        );

    private static final UUID CCCD_UUID =
        UUID.fromString(
            "00002902-0000-1000-8000-00805f9b34fb"
        );

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        boolean setupComplete =
            getSharedPreferences(
                "meraled_prefs",
                MODE_PRIVATE
            ).getBoolean(
                "setup_complete",
                false
            );

        if (setupComplete) {
            showMainWebApp();
            return;
        }

        buildSetupScreen();

        statusText.setText(
            "Durum: Bluetooth hazırlanıyor..."
        );

        initBle();
    }

    private void buildSetupScreen() {

        ScrollView scrollView =
            new ScrollView(this);

        scrollView.setFillViewport(true);
        scrollView.setBackgroundColor(
            Color.parseColor("#071321")
        );

        LinearLayout root =
            new LinearLayout(this);

        root.setOrientation(
            LinearLayout.VERTICAL
        );

        root.setPadding(
            dp(24),
            dp(42),
            dp(24),
            dp(32)
        );

        root.setBackgroundColor(
            Color.parseColor("#071321")
        );

        /*
         * MERALED marka basligi
         */
        ImageView logoView =
            new ImageView(this);

        int logoResId =
            getResources().getIdentifier(
                "meraled_logo",
                "drawable",
                getPackageName()
            );

        if (logoResId != 0) {
            logoView.setImageResource(
                logoResId
            );
        }

        logoView.setAdjustViewBounds(
            true
        );

        logoView.setScaleType(
            ImageView.ScaleType.CENTER_INSIDE
        );

        logoView.setContentDescription(
            "MERALED"
        );

        LinearLayout.LayoutParams logoParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(68)
            );

        logoParams.gravity =
            Gravity.CENTER_HORIZONTAL;

        root.addView(
            logoView,
            logoParams
        );


        /*
         * Marka alt basligi
         */
        TextView subtitle =
            new TextView(this);

        subtitle.setText(
            "SMART SHOWCASE LIGHTING"
        );

        subtitle.setTextSize(11);

        subtitle.setTextColor(
            Color.parseColor("#7589A7")
        );

        subtitle.setGravity(
            Gravity.CENTER
        );

        subtitle.setLetterSpacing(
            0.22f
        );

        LinearLayout.LayoutParams subtitleParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        subtitleParams.topMargin =
            dp(5);

        root.addView(
            subtitle,
            subtitleParams
        );


        /*
         * ILK KURULUM etiketi
         */
        TextView setupBadge =
            new TextView(this);

        setupBadge.setText(
            "İLK KURULUM"
        );

        setupBadge.setTextSize(
            11
        );

        setupBadge.setTextColor(
            Color.parseColor("#91B6FF")
        );

        setupBadge.setGravity(
            Gravity.CENTER
        );

        setupBadge.setLetterSpacing(
            0.16f
        );

        setupBadge.setPadding(
            dp(16),
            dp(8),
            dp(16),
            dp(8)
        );

        setupBadge.setBackground(
            roundedBackground(
                "#0C1D33",
                "#315A8C",
                18
            )
        );

        LinearLayout.LayoutParams badgeParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        badgeParams.gravity =
            Gravity.CENTER_HORIZONTAL;

        badgeParams.topMargin =
            dp(17);

        root.addView(
            setupBadge,
            badgeParams
        );


        /*
         * Premium kurulum adim gostergesi
         *
         * Duz Unicode tik / nokta kullanmak yerine
         * gercek durum daireleri ve baglanti cizgileri.
         */
        LinearLayout wizardStepper =
            new LinearLayout(this);

        wizardStepper.setOrientation(
            LinearLayout.HORIZONTAL
        );

        wizardStepper.setGravity(
            Gravity.CENTER_VERTICAL
        );

        wizardStepper.setPadding(
            dp(4),
            0,
            dp(4),
            0
        );


        /*
         * 1 - Cihaz
         */
        LinearLayout deviceStep =
            new LinearLayout(this);

        deviceStep.setOrientation(
            LinearLayout.VERTICAL
        );

        deviceStep.setGravity(
            Gravity.CENTER_HORIZONTAL
        );

        wizardStepDeviceCircle =
            createWizardStepCircle(
                "1"
            );

        deviceStep.addView(
            wizardStepDeviceCircle,
            new LinearLayout.LayoutParams(
                dp(36),
                dp(36)
            )
        );

        wizardStepDeviceLabel =
            createWizardStepLabel(
                "Cihaz"
            );

        LinearLayout.LayoutParams deviceLabelParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        deviceLabelParams.topMargin =
            dp(8);

        deviceStep.addView(
            wizardStepDeviceLabel,
            deviceLabelParams
        );

        LinearLayout.LayoutParams stepItemParams =
            new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f
            );

        wizardStepper.addView(
            deviceStep,
            stepItemParams
        );


        /*
         * Cihaz -> Wi-Fi cizgisi
         */
        wizardStepLineOne =
            new View(this);

        LinearLayout.LayoutParams lineOneParams =
            new LinearLayout.LayoutParams(
                dp(34),
                dp(2)
            );

        lineOneParams.gravity =
            Gravity.TOP;

        lineOneParams.topMargin =
            dp(17);

        wizardStepper.addView(
            wizardStepLineOne,
            lineOneParams
        );


        /*
         * 2 - Wi-Fi
         */
        LinearLayout wifiStep =
            new LinearLayout(this);

        wifiStep.setOrientation(
            LinearLayout.VERTICAL
        );

        wifiStep.setGravity(
            Gravity.CENTER_HORIZONTAL
        );

        wizardStepWifiCircle =
            createWizardStepCircle(
                "2"
            );

        wifiStep.addView(
            wizardStepWifiCircle,
            new LinearLayout.LayoutParams(
                dp(36),
                dp(36)
            )
        );

        wizardStepWifiLabel =
            createWizardStepLabel(
                "Wi-Fi"
            );

        LinearLayout.LayoutParams wifiLabelParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        wifiLabelParams.topMargin =
            dp(8);

        wifiStep.addView(
            wizardStepWifiLabel,
            wifiLabelParams
        );

        wizardStepper.addView(
            wifiStep,
            new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f
            )
        );


        /*
         * Wi-Fi -> Tamamla cizgisi
         */
        wizardStepLineTwo =
            new View(this);

        LinearLayout.LayoutParams lineTwoParams =
            new LinearLayout.LayoutParams(
                dp(34),
                dp(2)
            );

        lineTwoParams.gravity =
            Gravity.TOP;

        lineTwoParams.topMargin =
            dp(17);

        wizardStepper.addView(
            wizardStepLineTwo,
            lineTwoParams
        );


        /*
         * 3 - Tamamla
         */
        LinearLayout completeStep =
            new LinearLayout(this);

        completeStep.setOrientation(
            LinearLayout.VERTICAL
        );

        completeStep.setGravity(
            Gravity.CENTER_HORIZONTAL
        );

        wizardStepCompleteCircle =
            createWizardStepCircle(
                "3"
            );

        completeStep.addView(
            wizardStepCompleteCircle,
            new LinearLayout.LayoutParams(
                dp(36),
                dp(36)
            )
        );

        wizardStepCompleteLabel =
            createWizardStepLabel(
                "Tamamla"
            );

        LinearLayout.LayoutParams completeLabelParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        completeLabelParams.topMargin =
            dp(8);

        completeStep.addView(
            wizardStepCompleteLabel,
            completeLabelParams
        );

        wizardStepper.addView(
            completeStep,
            new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.WRAP_CONTENT,
                1.0f
            )
        );


        LinearLayout.LayoutParams wizardStepperParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        wizardStepperParams.topMargin =
            dp(22);

        root.addView(
            wizardStepper,
            wizardStepperParams
        );

        updateWizardStepper(
            1
        );


        /*
         * Ortak durum karti.
         * Tum kurulum adimlarinda gorunur.
         */
        LinearLayout globalStatusCard =
            new LinearLayout(this);

        globalStatusCard.setOrientation(
            LinearLayout.VERTICAL
        );

        globalStatusCard.setPadding(
            dp(16),
            dp(14),
            dp(16),
            dp(14)
        );

        globalStatusCard.setBackground(
            roundedBackground(
                "#0B1828",
                "#1E3654",
                16
            )
        );


        /*
         * Adim container'lari
         */
        setupStepBle =
            new LinearLayout(this);

        setupStepBle.setOrientation(
            LinearLayout.VERTICAL
        );


        setupStepWifi =
            new LinearLayout(this);

        setupStepWifi.setOrientation(
            LinearLayout.VERTICAL
        );

        setupStepWifi.setVisibility(
            View.GONE
        );


        setupStepComplete =
            new LinearLayout(this);

        setupStepComplete.setOrientation(
            LinearLayout.VERTICAL
        );

        setupStepComplete.setVisibility(
            View.GONE
        );

        /*
         * Bluetooth karti
         */
        LinearLayout card =
            new LinearLayout(this);

        card.setOrientation(
            LinearLayout.VERTICAL
        );

        card.setPadding(
            dp(20),
            dp(20),
            dp(20),
            dp(20)
        );

        card.setBackground(
            roundedBackground(
                "#0B1828",
                "#1E3654",
                22
            )
        );

        LinearLayout.LayoutParams cardParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        cardParams.topMargin = dp(28);

        setupStepBle.addView(
            card,
            cardParams
        );

        TextView cardTitle =
            new TextView(this);

        cardTitle.setText(
            "Bluetooth Kurulumu"
        );

        cardTitle.setTextSize(19);
        cardTitle.setTextColor(
            Color.parseColor("#F4F7FC")
        );

        card.addView(
            cardTitle
        );

        TextView cardDescription =
            new TextView(this);

        cardDescription.setText(
            "Yakındaki MERALED kontrol ünitesi aranacak."
        );

        cardDescription.setTextSize(14);
        cardDescription.setTextColor(
            Color.parseColor("#8290A5")
        );

        LinearLayout.LayoutParams descParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        descParams.topMargin = dp(6);

        card.addView(
            cardDescription,
            descParams
        );

        /*
         * Durum
         */
        TextView statusLabel =
            new TextView(this);

        statusLabel.setText("DURUM");
        statusLabel.setTextSize(11);
        statusLabel.setLetterSpacing(0.15f);
        statusLabel.setTextColor(
            Color.parseColor("#6687B5")
        );

        LinearLayout.LayoutParams statusLabelParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        statusLabelParams.topMargin = dp(24);

        globalStatusCard.addView(
            statusLabel,
            statusLabelParams
        );

        statusText =
            new TextView(this);

        statusText.setText(
            "Bluetooth hazırlanıyor..."
        );

        statusText.setTextSize(15);
        statusText.setTextColor(
            Color.parseColor("#D7DFEB")
        );

        LinearLayout.LayoutParams statusParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        statusParams.topMargin = dp(7);

        globalStatusCard.addView(
            statusText,
            statusParams
        );

        /*
         * Yakindaki cihaz
         */
        TextView nearbyTitle =
            new TextView(this);

        nearbyTitle.setText(
            "YAKINDAKİ CİHAZ"
        );

        nearbyTitle.setTextSize(11);
        nearbyTitle.setLetterSpacing(0.15f);
        nearbyTitle.setTextColor(
            Color.parseColor("#6687B5")
        );

        LinearLayout.LayoutParams nearbyParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        nearbyParams.topMargin = dp(24);

        card.addView(
            nearbyTitle,
            nearbyParams
        );

        deviceText =
            new TextView(this);

        deviceText.setText(
            "Henüz cihaz bulunamadı."
        );

        deviceText.setTextSize(17);
        deviceText.setTextColor(
            Color.parseColor("#A8B4C6")
        );

        deviceText.setPadding(
            dp(16),
            dp(16),
            dp(16),
            dp(16)
        );

        deviceText.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );

        LinearLayout.LayoutParams deviceParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        deviceParams.topMargin = dp(9);

        card.addView(
            deviceText,
            deviceParams
        );

        /*
         * Kurulum PIN
         */
        TextView pinTitle =
            new TextView(this);

        pinTitle.setText(
            "KURULUM PIN'İ"
        );

        pinTitle.setTextSize(11);
        pinTitle.setLetterSpacing(0.15f);
        pinTitle.setTextColor(
            Color.parseColor("#6687B5")
        );

        LinearLayout.LayoutParams pinTitleParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        pinTitleParams.topMargin = dp(20);

        setupStepBle.addView(
            pinTitle,
            pinTitleParams
        );

        setupPinInput =
            new EditText(this);

        setupPinInput.setHint(
            "8 haneli kurulum PIN'i"
        );

        setupPinInput.setSingleLine(true);

        setupPinInput.setInputType(
            InputType.TYPE_CLASS_NUMBER
            |
            InputType.TYPE_NUMBER_VARIATION_PASSWORD
        );

        setupPinInput.setTextSize(17);

        setupPinInput.setTextColor(
            Color.parseColor("#F5F7FB")
        );

        setupPinInput.setHintTextColor(
            Color.parseColor("#65758A")
        );

        setupPinInput.setPadding(
            dp(16),
            0,
            dp(16),
            0
        );

        setupPinInput.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );

        LinearLayout.LayoutParams pinInputParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(56)
            );

        pinInputParams.topMargin = dp(9);

        setupStepBle.addView(
            setupPinInput,
            pinInputParams
        );

        /*
         * Tarama butonu
         */
        scanButton =
            new Button(this);

        scanButton.setText(
            "CİHAZLARI TARA"
        );

        scanButton.setTextSize(14);
        scanButton.setAllCaps(false);
        scanButton.setGravity(Gravity.CENTER);
        scanButton.setPadding(0, 0, 0, 0);

        stylePrimaryButton(
            scanButton,
            true
        );

        LinearLayout.LayoutParams scanParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(58)
            );

        scanParams.topMargin = dp(24);

        setupStepBle.addView(
            scanButton,
            scanParams
        );

        /*
         * Baglan butonu
         */
        connectButton =
            new Button(this);

        connectButton.setText(
            "CİHAZA BAĞLAN"
        );

        connectButton.setTextSize(14);
        connectButton.setAllCaps(false);
        connectButton.setGravity(Gravity.CENTER);
        connectButton.setPadding(0, 0, 0, 0);

        connectButton.setEnabled(false);

        stylePrimaryButton(
            connectButton,
            false
        );

        LinearLayout.LayoutParams connectParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(58)
            );

        connectParams.topMargin = dp(12);

        setupStepBle.addView(
            connectButton,
            connectParams
        );


        bleNextButton =
            new Button(this);

        bleNextButton.setText(
            "İLERİ  ›"
        );

        bleNextButton.setTextSize(14);
        bleNextButton.setAllCaps(false);
        bleNextButton.setGravity(
            Gravity.CENTER
        );

        bleNextButton.setEnabled(
            false
        );

        stylePrimaryButton(
            bleNextButton,
            false
        );

        LinearLayout.LayoutParams bleNextParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(56)
            );

        bleNextParams.topMargin = dp(18);

        setupStepBle.addView(
            bleNextButton,
            bleNextParams
        );

        bleNextButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {

                    if (setupSessionActive) {
                        showSetupStep(2);
                    }
                }
            }
        );

        /*
         * Wi-Fi Kurulum
         *
         * SESSION_ACTIVE=1 gelene kadar gizli.
         */
        wifiSetupSection =
            new LinearLayout(this);

        wifiSetupSection.setOrientation(
            LinearLayout.VERTICAL
        );

        wifiSetupSection.setPadding(
            dp(16),
            dp(18),
            dp(16),
            dp(18)
        );

        wifiSetupSection.setBackground(
            roundedBackground(
                "#0B192A",
                "#203A59",
                16
            )
        );

        wifiSetupSection.setVisibility(
            View.GONE
        );

        LinearLayout.LayoutParams wifiSectionParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        wifiSectionParams.topMargin = dp(20);

        TextView wifiTitle =
            new TextView(this);

        wifiTitle.setText(
            "WI-FI AĞINI SEÇ"
        );

        wifiTitle.setTextSize(11);
        wifiTitle.setLetterSpacing(0.15f);
        wifiTitle.setTextColor(
            Color.parseColor("#6687B5")
        );

        wifiSetupSection.addView(
            wifiTitle
        );


        TextView wifiDescription =
            new TextView(this);

        wifiDescription.setText(
            "Yakındaki Wi-Fi ağlarından birini seçin. "
            + "Ardından yalnızca ağ şifresini girin."
        );

        wifiDescription.setTextSize(13);
        wifiDescription.setTextColor(
            Color.parseColor("#A8B4C6")
        );

        LinearLayout.LayoutParams wifiDescriptionParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        wifiDescriptionParams.topMargin = dp(8);

        wifiSetupSection.addView(
            wifiDescription,
            wifiDescriptionParams
        );


        /*
         * Yakindaki Wi-Fi aglari
         */
        wifiNetworkStatusText =
            new TextView(this);

        wifiNetworkStatusText.setText(
            "Yakındaki ağlar henüz taranmadı."
        );

        wifiNetworkStatusText.setTextSize(13);

        wifiNetworkStatusText.setTextColor(
            Color.parseColor("#8290A5")
        );

        LinearLayout.LayoutParams wifiStatusParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        wifiStatusParams.topMargin =
            dp(18);

        wifiSetupSection.addView(
            wifiNetworkStatusText,
            wifiStatusParams
        );


        wifiNetworkList =
            new LinearLayout(this);

        wifiNetworkList.setOrientation(
            LinearLayout.VERTICAL
        );

        LinearLayout.LayoutParams wifiListParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        wifiListParams.topMargin =
            dp(8);

        wifiSetupSection.addView(
            wifiNetworkList,
            wifiListParams
        );


        wifiRescanButton =
            new Button(this);

        wifiRescanButton.setText(
            "YENİDEN TARA"
        );

        wifiRescanButton.setTextSize(13);
        wifiRescanButton.setAllCaps(false);

        wifiRescanButton.setTextColor(
            Color.parseColor("#D7DFEB")
        );

        wifiRescanButton.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );

        LinearLayout.LayoutParams wifiRescanParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(48)
            );

        wifiRescanParams.topMargin =
            dp(10);

        wifiSetupSection.addView(
            wifiRescanButton,
            wifiRescanParams
        );


        wifiSelectedNetworkText =
            new TextView(this);

        wifiSelectedNetworkText.setText(
            "Seçilen ağ: Henüz seçilmedi"
        );

        wifiSelectedNetworkText.setTextSize(14);

        wifiSelectedNetworkText.setTextColor(
            Color.parseColor("#A8B4C6")
        );

        wifiSelectedNetworkText.setPadding(
            dp(16),
            dp(13),
            dp(16),
            dp(13)
        );

        wifiSelectedNetworkText.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );

        LinearLayout.LayoutParams selectedNetworkParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        selectedNetworkParams.topMargin =
            dp(16);

        wifiSetupSection.addView(
            wifiSelectedNetworkText,
            selectedNetworkParams
        );


        wifiSsidInput =
            new EditText(this);

        wifiSsidInput.setHint(
            "Wi-Fi adı (SSID)"
        );

        wifiSsidInput.setSingleLine(true);

        /*
         * Ana kullanim ag listesinden secimdir.
         * Bu alan sadece "Agi elle gir" icin acilir.
         */
        wifiSsidInput.setVisibility(
            View.GONE
        );

        wifiSsidInput.setInputType(
            InputType.TYPE_CLASS_TEXT
        );

        wifiSsidInput.setTextSize(16);

        wifiSsidInput.setTextColor(
            Color.parseColor("#F5F7FB")
        );

        wifiSsidInput.setHintTextColor(
            Color.parseColor("#65758A")
        );

        wifiSsidInput.setPadding(
            dp(16),
            0,
            dp(16),
            0
        );

        wifiSsidInput.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );

        LinearLayout.LayoutParams wifiSsidParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(56)
            );

        wifiSsidParams.topMargin = dp(16);

        wifiSetupSection.addView(
            wifiSsidInput,
            wifiSsidParams
        );


        wifiManualButton =
            new Button(this);

        wifiManualButton.setText(
            "AĞI ELLE GİR"
        );

        wifiManualButton.setTextSize(12);
        wifiManualButton.setAllCaps(false);

        wifiManualButton.setTextColor(
            Color.parseColor("#83AFFF")
        );

        wifiManualButton.setBackground(
            roundedBackground(
                "#0B192A",
                "#203A59",
                12
            )
        );

        LinearLayout.LayoutParams manualParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(44)
            );

        manualParams.topMargin =
            dp(8);

        wifiSetupSection.addView(
            wifiManualButton,
            manualParams
        );


        wifiPasswordInput =
            new EditText(this);

        wifiPasswordInput.setHint(
            "Wi-Fi şifresi"
        );

        wifiPasswordInput.setSingleLine(true);

        wifiPasswordInput.setInputType(
            InputType.TYPE_CLASS_TEXT
            |
            InputType.TYPE_TEXT_VARIATION_PASSWORD
        );

        wifiPasswordInput.setTextSize(16);

        wifiPasswordInput.setTextColor(
            Color.parseColor("#F5F7FB")
        );

        wifiPasswordInput.setHintTextColor(
            Color.parseColor("#65758A")
        );

        wifiPasswordInput.setPadding(
            dp(16),
            0,
            dp(16),
            0
        );

        wifiPasswordInput.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );

        LinearLayout.LayoutParams wifiPasswordParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(56)
            );

        wifiPasswordParams.topMargin = dp(10);

        wifiSetupSection.addView(
            wifiPasswordInput,
            wifiPasswordParams
        );


        wifiConnectButton =
            new Button(this);

        wifiConnectButton.setText(
            "WI-FI'YE BAĞLAN"
        );

        wifiConnectButton.setTextSize(14);
        wifiConnectButton.setAllCaps(false);
        wifiConnectButton.setGravity(
            Gravity.CENTER
        );

        wifiConnectButton.setPadding(
            0,
            0,
            0,
            0
        );

        /*
         * BLE write akisini sonraki adimda
         * baglayacagimiz icin simdilik pasif.
         */
        wifiConnectButton.setEnabled(
            false
        );

        stylePrimaryButton(
            wifiConnectButton,
            false
        );

        LinearLayout.LayoutParams wifiButtonParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(58)
            );

        wifiButtonParams.topMargin = dp(14);

        wifiSetupSection.addView(
            wifiConnectButton,
            wifiButtonParams
        );


        setupStepWifi.addView(
            wifiSetupSection,
            wifiSectionParams
        );

        wifiConnectButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    startWifiProvisioning();
                }
            }
        );


        wifiRescanButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    startWifiScan();
                }
            }
        );


        wifiManualButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {

                    wifiSsidInput.setVisibility(
                        View.VISIBLE
                    );

                    wifiSsidInput.requestFocus();

                    wifiSelectedNetworkText.setText(
                        "Ağ adı elle giriliyor."
                    );
                }
            }
        );


        /*
         * Wi-Fi navigasyon
         */
        LinearLayout wifiNavigation =
            new LinearLayout(this);

        wifiNavigation.setOrientation(
            LinearLayout.HORIZONTAL
        );

        LinearLayout.LayoutParams wifiNavParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(56)
            );

        wifiNavParams.topMargin = dp(16);


        wifiBackButton =
            new Button(this);

        wifiBackButton.setText(
            "‹  GERİ"
        );

        wifiBackButton.setTextSize(14);
        wifiBackButton.setAllCaps(false);

        wifiBackButton.setTextColor(
            Color.parseColor("#D7DFEB")
        );

        wifiBackButton.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );


        wifiNextButton =
            new Button(this);

        wifiNextButton.setText(
            "İLERİ  ›"
        );

        wifiNextButton.setTextSize(14);
        wifiNextButton.setAllCaps(false);

        wifiNextButton.setEnabled(
            false
        );

        stylePrimaryButton(
            wifiNextButton,
            false
        );


        LinearLayout.LayoutParams navButtonParams1 =
            new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.MATCH_PARENT,
                1.0f
            );

        navButtonParams1.rightMargin =
            dp(6);

        LinearLayout.LayoutParams navButtonParams2 =
            new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.MATCH_PARENT,
                1.0f
            );

        navButtonParams2.leftMargin =
            dp(6);

        wifiNavigation.addView(
            wifiBackButton,
            navButtonParams1
        );

        wifiNavigation.addView(
            wifiNextButton,
            navButtonParams2
        );

        setupStepWifi.addView(
            wifiNavigation,
            wifiNavParams
        );


        wifiBackButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    showSetupStep(1);
                }
            }
        );

        wifiNextButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {

                    if (setupWifiConnected) {
                        updateCompleteSummary();
                        showSetupStep(3);
                    }
                }
            }
        );


        /*
         * ADIM 3 - Tamamlama
         */
        LinearLayout completeCard =
            new LinearLayout(this);

        completeCard.setOrientation(
            LinearLayout.VERTICAL
        );

        completeCard.setPadding(
            dp(20),
            dp(24),
            dp(20),
            dp(24)
        );

        completeCard.setBackground(
            roundedBackground(
                "#0B1828",
                "#1E3654",
                22
            )
        );

        LinearLayout.LayoutParams completeCardParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        completeCardParams.topMargin =
            dp(28);


        TextView completeTitle =
            new TextView(this);

        completeTitle.setText(
            "✓  MERALED HAZIR"
        );

        completeTitle.setTextSize(22);

        completeTitle.setTextColor(
            Color.parseColor("#2EBE6E")
        );

        completeTitle.setGravity(
            Gravity.CENTER
        );

        completeCard.addView(
            completeTitle
        );


        TextView completeDescription =
            new TextView(this);

        completeDescription.setText(
            "Cihaz bağlantısı ve Wi-Fi kurulumu başarıyla tamamlandı."
        );

        completeDescription.setTextSize(14);

        completeDescription.setTextColor(
            Color.parseColor("#A8B4C6")
        );

        completeDescription.setGravity(
            Gravity.CENTER
        );

        LinearLayout.LayoutParams completeDescParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        completeDescParams.topMargin =
            dp(12);

        completeCard.addView(
            completeDescription,
            completeDescParams
        );


        completeSummaryText =
            new TextView(this);

        completeSummaryText.setText(
            "Wi-Fi: -\nIP: -"
        );

        completeSummaryText.setTextSize(15);

        completeSummaryText.setTextColor(
            Color.parseColor("#D7DFEB")
        );

        completeSummaryText.setPadding(
            dp(16),
            dp(16),
            dp(16),
            dp(16)
        );

        completeSummaryText.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );

        LinearLayout.LayoutParams summaryParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        summaryParams.topMargin =
            dp(22);

        completeCard.addView(
            completeSummaryText,
            summaryParams
        );


        setupStepComplete.addView(
            completeCard,
            completeCardParams
        );


        LinearLayout completeNavigation =
            new LinearLayout(this);

        completeNavigation.setOrientation(
            LinearLayout.HORIZONTAL
        );

        LinearLayout.LayoutParams completeNavParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(56)
            );

        completeNavParams.topMargin =
            dp(16);


        completeBackButton =
            new Button(this);

        completeBackButton.setText(
            "‹  GERİ"
        );

        completeBackButton.setTextSize(14);
        completeBackButton.setAllCaps(false);

        completeBackButton.setTextColor(
            Color.parseColor("#D7DFEB")
        );

        completeBackButton.setBackground(
            roundedBackground(
                "#0E1E31",
                "#203A59",
                14
            )
        );


        finishSetupButton =
            new Button(this);

        finishSetupButton.setText(
            "KURULUMU TAMAMLA"
        );

        finishSetupButton.setTextSize(14);
        finishSetupButton.setAllCaps(false);

        stylePrimaryButton(
            finishSetupButton,
            true
        );


        LinearLayout.LayoutParams completeButtonParams1 =
            new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.MATCH_PARENT,
                1.0f
            );

        completeButtonParams1.rightMargin =
            dp(6);

        LinearLayout.LayoutParams completeButtonParams2 =
            new LinearLayout.LayoutParams(
                0,
                LinearLayout.LayoutParams.MATCH_PARENT,
                1.4f
            );

        completeButtonParams2.leftMargin =
            dp(6);

        completeNavigation.addView(
            completeBackButton,
            completeButtonParams1
        );

        completeNavigation.addView(
            finishSetupButton,
            completeButtonParams2
        );

        setupStepComplete.addView(
            completeNavigation,
            completeNavParams
        );


        completeBackButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    showSetupStep(2);
                }
            }
        );

        finishSetupButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {

                    statusText.setText(
                        "MERALED açılıyor..."
                    );

                    getSharedPreferences(
                        "meraled_prefs",
                        MODE_PRIVATE
                    ).edit()
                        .putBoolean(
                            "setup_complete",
                            true
                        )
                        .apply();

                    showMainWebApp();
                }
            }
        );

        /*
         * Bilgilendirme
         */
        TextView info =
            new TextView(this);

        info.setText(
            "İlk kurulum sırasında telefonunuz Bluetooth "
            + "üzerinden MERALED kontrol ünitesini bulur. "
            + "Cihaz algılandığında bağlantı butonu otomatik "
            + "olarak aktif olacaktır."
        );

        info.setTextSize(13);
        info.setTextColor(
            Color.parseColor("#718096")
        );

        info.setLineSpacing(
            0.0f,
            1.18f
        );

        LinearLayout.LayoutParams infoParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        infoParams.topMargin = dp(24);

        setupStepBle.addView(
            info,
            infoParams
        );

        scanButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {
                    startBleScan();
                }
            }
        );

        connectButton.setOnClickListener(
            new View.OnClickListener() {
                @Override
                public void onClick(View view) {

                    if (foundDevice != null) {
                        connectToFoundDevice();
                    } else {
                        statusText.setText(
                            "Bağlanılacak MERALED cihazı bulunamadı."
                        );
                    }
                }
            }
        );

        LinearLayout.LayoutParams globalStatusParams =
            new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            );

        globalStatusParams.topMargin =
            dp(18);

        root.addView(
            globalStatusCard,
            globalStatusParams
        );


        root.addView(
            setupStepBle
        );

        root.addView(
            setupStepWifi
        );

        root.addView(
            setupStepComplete
        );


        showSetupStep(1);

        scrollView.addView(root);
        setContentView(scrollView);
    }


    private void showSetupStep(
        int step
    ) {

        if (
            setupStepBle == null
            || setupStepWifi == null
            || setupStepComplete == null
        ) {
            return;
        }

        setupStepBle.setVisibility(
            step == 1
            ? View.VISIBLE
            : View.GONE
        );

        setupStepWifi.setVisibility(
            step == 2
            ? View.VISIBLE
            : View.GONE
        );

        setupStepComplete.setVisibility(
            step == 3
            ? View.VISIBLE
            : View.GONE
        );

        if (
            step == 2
            && !wifiScanAttempted
        ) {
            wifiScanAttempted = true;
            startWifiScan();
        }

        updateWizardStepper(
            step
        );
    }


    private TextView createWizardStepCircle(
        String number
    ) {

        TextView circle =
            new TextView(this);

        circle.setText(
            number
        );

        circle.setTextSize(
            13
        );

        circle.setGravity(
            Gravity.CENTER
        );

        circle.setTextColor(
            Color.parseColor("#687A91")
        );

        return circle;
    }


    private TextView createWizardStepLabel(
        String label
    ) {

        TextView text =
            new TextView(this);

        text.setText(
            label
        );

        text.setTextSize(
            12
        );

        text.setGravity(
            Gravity.CENTER
        );

        text.setTextColor(
            Color.parseColor("#66768C")
        );

        return text;
    }


    private void styleWizardStepCircle(
        TextView circle,
        boolean complete,
        boolean active
    ) {

        if (circle == null) {
            return;
        }

        GradientDrawable background;

        if (active) {

            background =
                new GradientDrawable(
                    GradientDrawable.Orientation.LEFT_RIGHT,
                    new int[] {
                        Color.parseColor("#2869F6"),
                        Color.parseColor("#7557E8")
                    }
                );

            background.setStroke(
                dp(1),
                Color.parseColor("#7FA7FF")
            );

            circle.setTextColor(
                Color.WHITE
            );

            circle.setElevation(
                dp(4)
            );

        } else if (complete) {

            background =
                new GradientDrawable();

            background.setColor(
                Color.parseColor("#0D2A25")
            );

            background.setStroke(
                dp(1),
                Color.parseColor("#2EBE6E")
            );

            circle.setTextColor(
                Color.parseColor("#6FE1A2")
            );

            circle.setElevation(
                dp(2)
            );

        } else {

            background =
                new GradientDrawable();

            background.setColor(
                Color.parseColor("#0A1624")
            );

            background.setStroke(
                dp(1),
                Color.parseColor("#263A53")
            );

            circle.setTextColor(
                Color.parseColor("#687A91")
            );

            circle.setElevation(
                0
            );
        }

        background.setCornerRadius(
            dp(18)
        );

        circle.setBackground(
            background
        );
    }


    private void styleWizardStepLabel(
        TextView label,
        boolean complete,
        boolean active
    ) {

        if (label == null) {
            return;
        }

        if (active) {

            label.setTextColor(
                Color.parseColor("#A9C4FF")
            );

        } else if (complete) {

            label.setTextColor(
                Color.parseColor("#72D9A0")
            );

        } else {

            label.setTextColor(
                Color.parseColor("#66768C")
            );
        }
    }


    private void updateWizardStepper(
        int step
    ) {

        if (
            wizardStepDeviceCircle == null
            || wizardStepWifiCircle == null
            || wizardStepCompleteCircle == null
        ) {
            return;
        }

        boolean deviceComplete =
            step > 1;

        boolean deviceActive =
            step == 1;

        boolean wifiComplete =
            step > 2;

        boolean wifiActive =
            step == 2;

        /*
         * Tamamlama ekranina gelindiginde
         * ucuncu adim da tamamlanmis olarak gosterilir.
         */
        boolean completeComplete =
            step >= 3;

        styleWizardStepCircle(
            wizardStepDeviceCircle,
            deviceComplete,
            deviceActive
        );

        styleWizardStepCircle(
            wizardStepWifiCircle,
            wifiComplete,
            wifiActive
        );

        styleWizardStepCircle(
            wizardStepCompleteCircle,
            completeComplete,
            false
        );

        styleWizardStepLabel(
            wizardStepDeviceLabel,
            deviceComplete,
            deviceActive
        );

        styleWizardStepLabel(
            wizardStepWifiLabel,
            wifiComplete,
            wifiActive
        );

        styleWizardStepLabel(
            wizardStepCompleteLabel,
            completeComplete,
            false
        );

        if (wizardStepLineOne != null) {

            wizardStepLineOne.setBackgroundColor(
                Color.parseColor(
                    step >= 2
                    ? "#2E7BEF"
                    : "#23364E"
                )
            );
        }

        if (wizardStepLineTwo != null) {

            wizardStepLineTwo.setBackgroundColor(
                Color.parseColor(
                    step >= 3
                    ? "#2EBE6E"
                    : "#23364E"
                )
            );
        }
    }


    private void updateCompleteSummary() {

        if (completeSummaryText == null) {
            return;
        }

        String ssid =
            setupWifiSsid == null
            ? "-"
            : setupWifiSsid;

        String ip =
            setupWifiIp == null
            ? "-"
            : setupWifiIp;

        completeSummaryText.setText(
            "Wi-Fi: "
            + ssid
            + "\nIP: "
            + ip
        );
    }


    private boolean hasWifiScanPermissions() {

        if (
            checkSelfPermission(
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            return false;
        }

        if (Build.VERSION.SDK_INT >= 33) {

            return checkSelfPermission(
                NEARBY_WIFI_DEVICES_PERMISSION
            ) == PackageManager.PERMISSION_GRANTED;
        }

        return true;
    }


    private void requestWifiScanPermissions() {

        if (Build.VERSION.SDK_INT >= 33) {

            requestPermissions(
                new String[] {
                    Manifest.permission.ACCESS_FINE_LOCATION,
                    NEARBY_WIFI_DEVICES_PERMISSION
                },
                WIFI_PERMISSION_REQUEST
            );

        } else {

            requestPermissions(
                new String[] {
                    Manifest.permission.ACCESS_FINE_LOCATION
                },
                WIFI_PERMISSION_REQUEST
            );
        }
    }


    private void startWifiScan() {

        if (!hasWifiScanPermissions()) {

            statusText.setText(
                "Yakındaki Wi-Fi ağlarını görmek için izin gerekli."
            );

            if (wifiNetworkStatusText != null) {
                wifiNetworkStatusText.setText(
                    "Wi-Fi tarama izni bekleniyor..."
                );
            }

            requestWifiScanPermissions();
            return;
        }


        if (wifiManager == null) {

            wifiManager =
                (WifiManager)
                    getApplicationContext()
                        .getSystemService(
                            Context.WIFI_SERVICE
                        );
        }


        if (wifiManager == null) {

            statusText.setText(
                "Wi-Fi servisi kullanılamıyor."
            );

            return;
        }


        if (!wifiManager.isWifiEnabled()) {

            statusText.setText(
                "Telefonun Wi-Fi özelliğini açın."
            );

            if (wifiNetworkStatusText != null) {
                wifiNetworkStatusText.setText(
                    "Wi-Fi kapalı."
                );
            }

            return;
        }


        if (wifiNetworkStatusText != null) {
            wifiNetworkStatusText.setText(
                "Yakındaki Wi-Fi ağları aranıyor..."
            );
        }


        boolean scanStarted = false;

        try {

            scanStarted =
                wifiManager.startScan();

        } catch (SecurityException exc) {

            statusText.setText(
                "Wi-Fi tarama izni kullanılamadı."
            );

            return;

        } catch (Exception exc) {

            statusText.setText(
                "Wi-Fi taraması başlatılamadı."
            );

            return;
        }


        /*
         * Android tarama throttling nedeniyle startScan()
         * false donese bile son scan sonuclarini kullanabiliriz.
         */
        handler.postDelayed(
            new Runnable() {
                @Override
                public void run() {
                    loadWifiScanResults();
                }
            },
            scanStarted
                ? 2500
                : 500
        );
    }


    private void loadWifiScanResults() {

        if (
            wifiManager == null
            || wifiNetworkList == null
        ) {
            return;
        }


        List<android.net.wifi.ScanResult> rawResults;

        try {

            rawResults =
                wifiManager.getScanResults();

        } catch (SecurityException exc) {

            statusText.setText(
                "Wi-Fi ağ listesi için izin gerekli."
            );

            return;

        } catch (Exception exc) {

            statusText.setText(
                "Wi-Fi ağ listesi alınamadı."
            );

            return;
        }


        wifiNetworkList.removeAllViews();


        if (
            rawResults == null
            || rawResults.isEmpty()
        ) {

            wifiNetworkStatusText.setText(
                "Ağ bulunamadı. Wi-Fi ve Konum açık olmalı."
            );

            return;
        }


        /*
         * Ayni SSID birden fazla access point'ten gelirse
         * en guclu sinyali tut.
         */
        Map<String, android.net.wifi.ScanResult> strongestBySsid =
            new HashMap<String, android.net.wifi.ScanResult>();


        for (android.net.wifi.ScanResult result : rawResults) {

            if (result == null) {
                continue;
            }

            String ssid =
                result.SSID == null
                ? ""
                : result.SSID.trim();

            /*
             * Hidden SSID'leri ana listede gostermiyoruz.
             * Manuel giris secenegi mevcut.
             */
            if (ssid.isEmpty()) {
                continue;
            }


            android.net.wifi.ScanResult existing =
                strongestBySsid.get(
                    ssid
                );

            if (
                existing == null
                || result.level > existing.level
            ) {
                strongestBySsid.put(
                    ssid,
                    result
                );
            }
        }


        List<android.net.wifi.ScanResult> networks =
            new ArrayList<android.net.wifi.ScanResult>(
                strongestBySsid.values()
            );


        Collections.sort(
            networks,
            new Comparator<android.net.wifi.ScanResult>() {
                @Override
                public int compare(
                    android.net.wifi.ScanResult a,
                    android.net.wifi.ScanResult b
                ) {
                    return b.level - a.level;
                }
            }
        );


        if (networks.isEmpty()) {

            wifiNetworkStatusText.setText(
                "Görünür Wi-Fi ağı bulunamadı."
            );

            return;
        }


        wifiNetworkStatusText.setText(
            networks.size()
            + " Wi-Fi ağı bulundu."
        );


        for (android.net.wifi.ScanResult result : networks) {

            final String ssid =
                result.SSID.trim();

            final int level =
                result.level;


            Button networkButton =
                new Button(this);

            networkButton.setAllCaps(
                false
            );

            networkButton.setGravity(
                Gravity.CENTER_VERTICAL
            );

            networkButton.setPadding(
                dp(16),
                0,
                dp(16),
                0
            );

            networkButton.setTextColor(
                Color.parseColor("#F5F7FB")
            );

            networkButton.setTextSize(
                14
            );

            networkButton.setText(
                ssid
                + "     "
                + wifiSignalLabel(level)
            );

            networkButton.setBackground(
                roundedBackground(
                    "#0E1E31",
                    "#203A59",
                    14
                )
            );


            LinearLayout.LayoutParams networkParams =
                new LinearLayout.LayoutParams(
                    LinearLayout.LayoutParams.MATCH_PARENT,
                    dp(54)
                );

            networkParams.topMargin =
                dp(7);


            networkButton.setOnClickListener(
                new View.OnClickListener() {
                    @Override
                    public void onClick(
                        View view
                    ) {

                        selectedWifiSsid =
                            ssid;

                        wifiSsidInput.setText(
                            ssid
                        );

                        wifiSsidInput.setVisibility(
                            View.GONE
                        );

                        wifiSelectedNetworkText.setText(
                            "Seçilen ağ: "
                            + ssid
                        );

                        statusText.setText(
                            "Wi-Fi ağı seçildi. Şifreyi girin."
                        );
                    }
                }
            );


            wifiNetworkList.addView(
                networkButton,
                networkParams
            );
        }
    }


    private String wifiSignalLabel(
        int level
    ) {

        if (level >= -55) {
            return "●●●●";
        }

        if (level >= -65) {
            return "●●●○";
        }

        if (level >= -75) {
            return "●●○○";
        }

        return "●○○○";
    }


    private void showMainWebApp() {

        webView =
            new WebView(this);

        WebSettings settings =
            webView.getSettings();

        settings.setJavaScriptEnabled(
            true
        );

        settings.setDomStorageEnabled(
            true
        );

        settings.setLoadWithOverviewMode(
            true
        );

        settings.setUseWideViewPort(
            true
        );


        webView.setWebViewClient(
            new WebViewClient()
        );

        webView.setWebChromeClient(
            new WebChromeClient()
        );


        setContentView(
            webView
        );


        webView.loadUrl(
            MERALED_MAIN_URL
        );
    }


    private GradientDrawable roundedBackground(
        String fillColor,
        String strokeColor,
        int radiusDp
    ) {

        GradientDrawable drawable =
            new GradientDrawable();

        drawable.setColor(
            Color.parseColor(fillColor)
        );

        drawable.setCornerRadius(
            dp(radiusDp)
        );

        drawable.setStroke(
            dp(1),
            Color.parseColor(strokeColor)
        );

        return drawable;
    }


    private GradientDrawable primaryGradient() {

        GradientDrawable drawable =
            new GradientDrawable(
                GradientDrawable.Orientation.LEFT_RIGHT,
                new int[] {
                    Color.parseColor("#2563EB"),
                    Color.parseColor("#7157D9"),
                    Color.parseColor("#E83E5A")
                }
            );

        drawable.setCornerRadius(
            dp(18)
        );

        return drawable;
    }


    private void stylePrimaryButton(
        Button button,
        boolean enabled
    ) {

        button.setEnabled(enabled);

        if (enabled) {

            button.setTextColor(
                Color.WHITE
            );

            button.setBackground(
                primaryGradient()
            );

            button.setAlpha(1.0f);

        } else {

            button.setTextColor(
                Color.parseColor("#65758A")
            );

            button.setBackground(
                roundedBackground(
                    "#111D2C",
                    "#1E3046",
                    18
                )
            );

            button.setAlpha(1.0f);
        }
    }


    private void initBle() {

        BluetoothManager manager =
            (BluetoothManager)
                getSystemService(
                    Context.BLUETOOTH_SERVICE
                );

        if (manager == null) {
            statusText.setText(
                "HATA: Bluetooth desteklenmiyor."
            );
            return;
        }

        bluetoothAdapter =
            manager.getAdapter();

        if (bluetoothAdapter == null) {
            statusText.setText(
                "HATA: Bluetooth adaptörü bulunamadı."
            );
            return;
        }

        if (!bluetoothAdapter.isEnabled()) {
            statusText.setText(
                "Bluetooth kapalı. "
                + "Lütfen Bluetooth'u açın."
            );
            return;
        }

        if (!hasBlePermissions()) {
            statusText.setText(
                "Bluetooth izni bekleniyor..."
            );

            requestBlePermissions();
            return;
        }

        startBleScan();
    }

    private boolean hasBlePermissions() {

        if (Build.VERSION.SDK_INT >= 31) {

            return checkSelfPermission(
                BLUETOOTH_SCAN_PERMISSION
            ) == PackageManager.PERMISSION_GRANTED
                &&
                checkSelfPermission(
                    BLUETOOTH_CONNECT_PERMISSION
                ) == PackageManager.PERMISSION_GRANTED
                &&
                checkSelfPermission(
                    Manifest.permission.ACCESS_COARSE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED
                &&
                checkSelfPermission(
                    Manifest.permission.ACCESS_FINE_LOCATION
                ) == PackageManager.PERMISSION_GRANTED;
        }

        return checkSelfPermission(
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED;
    }

    private void requestBlePermissions() {

        if (Build.VERSION.SDK_INT >= 31) {

            requestPermissions(
                new String[] {
                    BLUETOOTH_SCAN_PERMISSION,
                    BLUETOOTH_CONNECT_PERMISSION,
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                    Manifest.permission.ACCESS_FINE_LOCATION
                },
                BLE_PERMISSION_REQUEST
            );

        } else {

            requestPermissions(
                new String[] {
                    Manifest.permission.ACCESS_FINE_LOCATION
                },
                BLE_PERMISSION_REQUEST
            );
        }
    }

    private void startBleScan() {

        if (!hasBlePermissions()) {
            statusText.setText(
                "Bluetooth izni verilmedi."
            );
            return;
        }

        if (
            bluetoothAdapter == null
            || !bluetoothAdapter.isEnabled()
        ) {
            statusText.setText(
                "Bluetooth kapalı."
            );
            return;
        }

        bleScanner =
            bluetoothAdapter
                .getBluetoothLeScanner();

        if (bleScanner == null) {
            statusText.setText(
                "HATA: BLE tarayıcı başlatılamadı."
            );
            return;
        }

        foundDeviceName = null;
        foundDevice = null;

        deviceText.setText(
            "Cihaz aranıyor..."
        );

        stylePrimaryButton(
            connectButton,
            false
        );

        stylePrimaryButton(
            scanButton,
            false
        );

        scanButton.setText("TARANIYOR...");

        statusText.setText(
            "Durum: Yakındaki MERALED cihazları aranıyor..."
        );

        handler.postDelayed(
            new Runnable() {
                @Override
                public void run() {

                    stopBleScan();

                    stylePrimaryButton(
                        scanButton,
                        true
                    );

                    scanButton.setText(
                        "TEKRAR TARA"
                    );

                    if (foundDeviceName == null) {

                        statusText.setText(
                            "Durum: Tarama tamamlandı."
                        );

                        deviceText.setText(
                            "MERALED cihazı bulunamadı."
                        );
                    }
                }
            },
            SCAN_PERIOD_MS
        );

        try {
            ScanSettings scanSettings =
                new ScanSettings.Builder()
                    .setScanMode(
                        ScanSettings.SCAN_MODE_LOW_LATENCY
                    )
                    .build();

            bleScanner.startScan(
                null,
                scanSettings,
                scanCallback
            );
        } catch (Exception e) {

            stylePrimaryButton(
                scanButton,
                true
            );

            scanButton.setText(
                "TEKRAR TARA"
            );

            statusText.setText(
                "BLE tarama hatası: "
                + e.getClass().getSimpleName()
            );
        }
    }

    private void connectToFoundDevice() {

        if (!hasBlePermissions()) {
            statusText.setText(
                "Bluetooth bağlantı izni verilmedi."
            );
            return;
        }

        if (foundDevice == null) {
            statusText.setText(
                "Bağlanılacak cihaz bulunamadı."
            );
            return;
        }

        String enteredPin = "";

        if (setupPinInput != null) {
            enteredPin =
                setupPinInput
                    .getText()
                    .toString()
                    .trim();
        }

        if (!enteredPin.matches("[0-9]{8}")) {
            statusText.setText(
                "8 haneli kurulum PIN'ini girin."
            );
            return;
        }

        pendingSetupPin =
            enteredPin;

        stopBleScan();

        if (bluetoothGatt != null) {
            try {
                bluetoothGatt.close();
            } catch (Exception ignored) {
            }

            bluetoothGatt = null;
        }

        statusText.setText(
            foundDeviceName
            + " cihazına bağlanılıyor..."
        );

        stylePrimaryButton(
            connectButton,
            false
        );

        try {
            bluetoothGatt =
                foundDevice.connectGatt(
                    this,
                    false,
                    gattCallback,
                    BluetoothDevice.TRANSPORT_LE
                );

            if (bluetoothGatt == null) {
                statusText.setText(
                    "BLE bağlantısı başlatılamadı."
                );

                stylePrimaryButton(
                    connectButton,
                    true
                );
            }

        } catch (Exception e) {

            statusText.setText(
                "BLE bağlantı hatası: "
                + e.getClass().getSimpleName()
            );

            stylePrimaryButton(
                connectButton,
                true
            );
        }
    }


    private void prepareAuthentication(
        BluetoothGatt gatt
    ) {

        BluetoothGattService service =
            gatt.getService(
                MERALED_SERVICE_UUID
            );

        if (service == null) {
            runOnUiThread(
                new Runnable() {
                    @Override
                    public void run() {
                        statusText.setText(
                            "MERALED BLE servisi bulunamadı."
                        );

                        stylePrimaryButton(
                            connectButton,
                            true
                        );
                    }
                }
            );
            return;
        }

        authCharacteristic =
            service.getCharacteristic(
                AUTH_UUID
            );

        if (authCharacteristic == null) {
            runOnUiThread(
                new Runnable() {
                    @Override
                    public void run() {
                        statusText.setText(
                            "MERALED AUTH karakteristiği bulunamadı."
                        );

                        stylePrimaryButton(
                            connectButton,
                            true
                        );
                    }
                }
            );
            return;
        }

        boolean notifyEnabled =
            gatt.setCharacteristicNotification(
                authCharacteristic,
                true
            );

        BluetoothGattDescriptor descriptor =
            authCharacteristic.getDescriptor(
                CCCD_UUID
            );

        if (
            !notifyEnabled
            || descriptor == null
        ) {
            runOnUiThread(
                new Runnable() {
                    @Override
                    public void run() {
                        statusText.setText(
                            "AUTH bildirim kanalı açılamadı."
                        );

                        stylePrimaryButton(
                            connectButton,
                            true
                        );
                    }
                }
            );
            return;
        }

        descriptor.setValue(
            BluetoothGattDescriptor
                .ENABLE_NOTIFICATION_VALUE
        );

        boolean started =
            gatt.writeDescriptor(
                descriptor
            );

        runOnUiThread(
            new Runnable() {
                @Override
                public void run() {

                    if (started) {
                        statusText.setText(
                            "Kimlik doğrulama hazırlanıyor..."
                        );
                    } else {
                        statusText.setText(
                            "AUTH bildirim ayarı gönderilemedi."
                        );

                        stylePrimaryButton(
                            connectButton,
                            true
                        );
                    }
                }
            }
        );
    }


    private void writeAuthenticationPin(
        BluetoothGatt gatt
    ) {

        if (
            authCharacteristic == null
            || pendingSetupPin == null
        ) {
            return;
        }

        authCharacteristic.setValue(
            pendingSetupPin.getBytes()
        );

        final boolean started =
            gatt.writeCharacteristic(
                authCharacteristic
            );

        runOnUiThread(
            new Runnable() {
                @Override
                public void run() {

                    if (started) {
                        statusText.setText(
                            "Kurulum PIN'i doğrulanıyor..."
                        );
                    } else {
                        statusText.setText(
                            "Kurulum PIN'i gönderilemedi."
                        );

                        stylePrimaryButton(
                            connectButton,
                            true
                        );
                    }
                }
            }
        );
    }


    private void prepareSession(
        BluetoothGatt gatt
    ) {

        BluetoothGattService service =
            gatt.getService(
                MERALED_SERVICE_UUID
            );

        if (service == null) {
            runOnUiThread(
                new Runnable() {
                    @Override
                    public void run() {
                        statusText.setText(
                            "SESSION için MERALED servisi bulunamadı."
                        );
                    }
                }
            );
            return;
        }

        sessionCharacteristic =
            service.getCharacteristic(
                SESSION_UUID
            );

        if (sessionCharacteristic == null) {
            runOnUiThread(
                new Runnable() {
                    @Override
                    public void run() {
                        statusText.setText(
                            "SESSION karakteristiği bulunamadı."
                        );
                    }
                }
            );
            return;
        }

        boolean notifyEnabled =
            gatt.setCharacteristicNotification(
                sessionCharacteristic,
                true
            );

        BluetoothGattDescriptor descriptor =
            sessionCharacteristic.getDescriptor(
                CCCD_UUID
            );

        if (
            !notifyEnabled
            || descriptor == null
        ) {
            runOnUiThread(
                new Runnable() {
                    @Override
                    public void run() {
                        statusText.setText(
                            "SESSION bildirim kanalı açılamadı."
                        );
                    }
                }
            );
            return;
        }

        descriptor.setValue(
            BluetoothGattDescriptor
                .ENABLE_NOTIFICATION_VALUE
        );

        final boolean started =
            gatt.writeDescriptor(
                descriptor
            );

        runOnUiThread(
            new Runnable() {
                @Override
                public void run() {

                    if (started) {
                        statusText.setText(
                            "Kurulum oturumu hazırlanıyor..."
                        );
                    } else {
                        statusText.setText(
                            "SESSION bildirim ayarı gönderilemedi."
                        );
                    }
                }
            }
        );
    }


    private void writeSessionStart(
        BluetoothGatt gatt
    ) {

        if (sessionCharacteristic == null) {
            return;
        }

        sessionCharacteristic.setValue(
            "START".getBytes()
        );

        final boolean started =
            gatt.writeCharacteristic(
                sessionCharacteristic
            );

        runOnUiThread(
            new Runnable() {
                @Override
                public void run() {

                    if (started) {
                        statusText.setText(
                            "Kurulum oturumu başlatılıyor..."
                        );
                    } else {
                        statusText.setText(
                            "SESSION START gönderilemedi."
                        );
                    }
                }
            }
        );
    }


    private void prepareWifiProvisioning(
        BluetoothGatt gatt
    ) {

        BluetoothGattService service =
            gatt.getService(
                MERALED_SERVICE_UUID
            );

        if (service == null) {
            statusText.setText(
                "Wi-Fi için MERALED servisi bulunamadı."
            );
            return;
        }

        wifiSsidCharacteristic =
            service.getCharacteristic(
                WIFI_SSID_UUID
            );

        wifiPasswordCharacteristic =
            service.getCharacteristic(
                WIFI_PASSWORD_UUID
            );

        wifiCommandCharacteristic =
            service.getCharacteristic(
                WIFI_COMMAND_UUID
            );

        wifiStatusCharacteristic =
            service.getCharacteristic(
                WIFI_STATUS_UUID
            );

        if (
            wifiSsidCharacteristic == null
            || wifiPasswordCharacteristic == null
            || wifiCommandCharacteristic == null
            || wifiStatusCharacteristic == null
        ) {
            statusText.setText(
                "Wi-Fi BLE karakteristikleri bulunamadı."
            );
            return;
        }

        boolean notifyEnabled =
            gatt.setCharacteristicNotification(
                wifiStatusCharacteristic,
                true
            );

        BluetoothGattDescriptor descriptor =
            wifiStatusCharacteristic.getDescriptor(
                CCCD_UUID
            );

        if (
            !notifyEnabled
            || descriptor == null
        ) {
            statusText.setText(
                "Wi-Fi durum bildirim kanalı açılamadı."
            );
            return;
        }

        descriptor.setValue(
            BluetoothGattDescriptor
                .ENABLE_NOTIFICATION_VALUE
        );

        final boolean started =
            gatt.writeDescriptor(
                descriptor
            );

        if (!started) {
            statusText.setText(
                "Wi-Fi bildirim ayarı gönderilemedi."
            );
        }
    }


    private void startWifiProvisioning() {

        if (
            bluetoothGatt == null
            || wifiSsidCharacteristic == null
            || wifiPasswordCharacteristic == null
            || wifiCommandCharacteristic == null
        ) {
            statusText.setText(
                "Wi-Fi BLE bağlantısı hazır değil."
            );
            return;
        }

        String ssid =
            wifiSsidInput == null
            ? ""
            : wifiSsidInput
                .getText()
                .toString()
                .trim();

        String password =
            wifiPasswordInput == null
            ? ""
            : wifiPasswordInput
                .getText()
                .toString();

        if (ssid.isEmpty()) {
            statusText.setText(
                "Wi-Fi adını (SSID) girin."
            );
            return;
        }

        pendingWifiSsid = ssid;
        pendingWifiPassword = password;

        wifiConnectButton.setEnabled(
            false
        );

        stylePrimaryButton(
            wifiConnectButton,
            false
        );

        writeWifiSsid(
            bluetoothGatt
        );
    }


    private void writeWifiSsid(
        BluetoothGatt gatt
    ) {

        if (
            wifiSsidCharacteristic == null
            || pendingWifiSsid == null
        ) {
            return;
        }

        wifiSsidCharacteristic.setValue(
            pendingWifiSsid.getBytes()
        );

        final boolean started =
            gatt.writeCharacteristic(
                wifiSsidCharacteristic
            );

        if (started) {
            statusText.setText(
                "Wi-Fi adı gönderiliyor..."
            );
        } else {
            statusText.setText(
                "Wi-Fi adı gönderilemedi."
            );

            wifiConnectButton.setEnabled(
                true
            );

            stylePrimaryButton(
                wifiConnectButton,
                true
            );
        }
    }


    private void writeWifiPassword(
        BluetoothGatt gatt
    ) {

        if (
            wifiPasswordCharacteristic == null
            || pendingWifiPassword == null
        ) {
            return;
        }

        wifiPasswordCharacteristic.setValue(
            pendingWifiPassword.getBytes()
        );

        final boolean started =
            gatt.writeCharacteristic(
                wifiPasswordCharacteristic
            );

        if (started) {
            statusText.setText(
                "Wi-Fi şifresi gönderiliyor..."
            );
        } else {
            statusText.setText(
                "Wi-Fi şifresi gönderilemedi."
            );

            wifiConnectButton.setEnabled(
                true
            );

            stylePrimaryButton(
                wifiConnectButton,
                true
            );
        }
    }


    private void writeWifiConnectCommand(
        BluetoothGatt gatt
    ) {

        if (wifiCommandCharacteristic == null) {
            return;
        }

        wifiCommandCharacteristic.setValue(
            "CONNECT".getBytes()
        );

        final boolean started =
            gatt.writeCharacteristic(
                wifiCommandCharacteristic
            );

        if (started) {
            statusText.setText(
                "Wi-Fi bağlantısı başlatılıyor..."
            );
        } else {
            statusText.setText(
                "Wi-Fi CONNECT komutu gönderilemedi."
            );

            wifiConnectButton.setEnabled(
                true
            );

            stylePrimaryButton(
                wifiConnectButton,
                true
            );
        }
    }


    private final BluetoothGattCallback gattCallback =
        new BluetoothGattCallback() {

            @Override
            public void onConnectionStateChange(
                final BluetoothGatt gatt,
                final int status,
                final int newState
            ) {

                if (
                    status == BluetoothGatt.GATT_SUCCESS
                    &&
                    newState
                        == BluetoothProfile.STATE_CONNECTED
                ) {

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {
                                statusText.setText(
                                    "BLE bağlantısı kuruldu. "
                                    + "Servisler aranıyor..."
                                );
                            }
                        }
                    );

                    boolean discoveryStarted = false;

                    try {
                        discoveryStarted =
                            gatt.discoverServices();
                    } catch (Exception ignored) {
                    }

                    if (!discoveryStarted) {
                        runOnUiThread(
                            new Runnable() {
                                @Override
                                public void run() {
                                    statusText.setText(
                                        "Servis keşfi başlatılamadı."
                                    );

                                    stylePrimaryButton(
                                        connectButton,
                                        true
                                    );
                                }
                            }
                        );
                    }

                } else if (
                    newState
                        == BluetoothProfile.STATE_DISCONNECTED
                ) {

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {
                                statusText.setText(
                                    "BLE bağlantısı kesildi. Kod: "
                                    + status
                                );

                                stylePrimaryButton(
                                    connectButton,
                                    foundDevice != null
                                );
                            }
                        }
                    );

                } else if (
                    status != BluetoothGatt.GATT_SUCCESS
                ) {

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {
                                statusText.setText(
                                    "BLE bağlantı hatası. Kod: "
                                    + status
                                );

                                stylePrimaryButton(
                                    connectButton,
                                    foundDevice != null
                                );
                            }
                        }
                    );
                }
            }

            @Override
            public void onServicesDiscovered(
                BluetoothGatt gatt,
                final int status
            ) {

                runOnUiThread(
                    new Runnable() {
                        @Override
                        public void run() {

                            if (
                                status
                                    == BluetoothGatt.GATT_SUCCESS
                            ) {
                                prepareAuthentication(
                                    gatt
                                );
                            } else {
                                statusText.setText(
                                    "BLE servis keşfi başarısız. Kod: "
                                    + status
                                );

                                stylePrimaryButton(
                                    connectButton,
                                    true
                                );
                            }
                        }
                    }
                );
            }


            @Override
            public void onDescriptorWrite(
                BluetoothGatt gatt,
                BluetoothGattDescriptor descriptor,
                final int status
            ) {

                if (
                    descriptor == null
                    || !CCCD_UUID.equals(
                        descriptor.getUuid()
                    )
                ) {
                    return;
                }

                BluetoothGattCharacteristic characteristic =
                    descriptor.getCharacteristic();

                if (characteristic == null) {
                    return;
                }

                final UUID characteristicUuid =
                    characteristic.getUuid();

                if (
                    !AUTH_UUID.equals(characteristicUuid)
                    && !SESSION_UUID.equals(characteristicUuid)
                    && !WIFI_STATUS_UUID.equals(characteristicUuid)
                ) {
                    return;
                }

                if (status != BluetoothGatt.GATT_SUCCESS) {

                    final String channelName;

                    if (AUTH_UUID.equals(characteristicUuid)) {
                        channelName = "AUTH";
                    } else if (
                        SESSION_UUID.equals(characteristicUuid)
                    ) {
                        channelName = "SESSION";
                    } else {
                        channelName = "WI-FI STATUS";
                    }

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {

                                statusText.setText(
                                    channelName
                                    + " bildirim ayarı başarısız. Kod: "
                                    + status
                                );

                                if (
                                    WIFI_STATUS_UUID.equals(
                                        characteristicUuid
                                    )
                                ) {
                                    wifiConnectButton.setEnabled(
                                        true
                                    );

                                    stylePrimaryButton(
                                        wifiConnectButton,
                                        true
                                    );
                                } else {
                                    stylePrimaryButton(
                                        connectButton,
                                        true
                                    );
                                }
                            }
                        }
                    );

                    return;
                }

                if (AUTH_UUID.equals(characteristicUuid)) {

                    writeAuthenticationPin(
                        gatt
                    );

                } else if (
                    SESSION_UUID.equals(characteristicUuid)
                ) {

                    writeSessionStart(
                        gatt
                    );

                } else if (
                    WIFI_STATUS_UUID.equals(characteristicUuid)
                ) {

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {

                                wifiConnectButton.setEnabled(
                                    true
                                );

                                stylePrimaryButton(
                                    wifiConnectButton,
                                    true
                                );

                                statusText.setText(
                                    "Wi-Fi bağlantısı için hazır."
                                );
                            }
                        }
                    );
                }
            }


            @Override
            public void onCharacteristicWrite(
                final BluetoothGatt gatt,
                BluetoothGattCharacteristic characteristic,
                final int status
            ) {

                if (characteristic == null) {
                    return;
                }

                final UUID characteristicUuid =
                    characteristic.getUuid();

                if (
                    !AUTH_UUID.equals(characteristicUuid)
                    && !SESSION_UUID.equals(characteristicUuid)
                    && !WIFI_SSID_UUID.equals(characteristicUuid)
                    && !WIFI_PASSWORD_UUID.equals(characteristicUuid)
                    && !WIFI_COMMAND_UUID.equals(characteristicUuid)
                ) {
                    return;
                }

                if (status != BluetoothGatt.GATT_SUCCESS) {

                    final String operationName;

                    if (AUTH_UUID.equals(characteristicUuid)) {
                        operationName = "PIN yazma";
                    } else if (
                        SESSION_UUID.equals(characteristicUuid)
                    ) {
                        operationName = "SESSION START";
                    } else if (
                        WIFI_SSID_UUID.equals(characteristicUuid)
                    ) {
                        operationName = "Wi-Fi adı gönderme";
                    } else if (
                        WIFI_PASSWORD_UUID.equals(characteristicUuid)
                    ) {
                        operationName = "Wi-Fi şifresi gönderme";
                    } else {
                        operationName = "Wi-Fi CONNECT";
                    }

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {

                                statusText.setText(
                                    operationName
                                    + " işlemi başarısız. Kod: "
                                    + status
                                );

                                if (
                                    WIFI_SSID_UUID.equals(characteristicUuid)
                                    || WIFI_PASSWORD_UUID.equals(characteristicUuid)
                                    || WIFI_COMMAND_UUID.equals(characteristicUuid)
                                ) {

                                    wifiConnectButton.setEnabled(
                                        true
                                    );

                                    stylePrimaryButton(
                                        wifiConnectButton,
                                        true
                                    );

                                } else {

                                    stylePrimaryButton(
                                        connectButton,
                                        true
                                    );
                                }
                            }
                        }
                    );

                    return;
                }


                if (
                    WIFI_SSID_UUID.equals(
                        characteristicUuid
                    )
                ) {

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {
                                writeWifiPassword(
                                    gatt
                                );
                            }
                        }
                    );

                } else if (
                    WIFI_PASSWORD_UUID.equals(
                        characteristicUuid
                    )
                ) {

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {
                                writeWifiConnectCommand(
                                    gatt
                                );
                            }
                        }
                    );

                } else if (
                    WIFI_COMMAND_UUID.equals(
                        characteristicUuid
                    )
                ) {

                    runOnUiThread(
                        new Runnable() {
                            @Override
                            public void run() {
                                statusText.setText(
                                    "Wi-Fi bağlantı sonucu bekleniyor..."
                                );
                            }
                        }
                    );
                }
            }


            @Override
            public void onCharacteristicChanged(
                final BluetoothGatt gatt,
                BluetoothGattCharacteristic characteristic
            ) {

                if (characteristic == null) {
                    return;
                }

                final UUID characteristicUuid =
                    characteristic.getUuid();

                if (
                    !AUTH_UUID.equals(characteristicUuid)
                    && !SESSION_UUID.equals(characteristicUuid)
                    && !WIFI_STATUS_UUID.equals(characteristicUuid)
                ) {
                    return;
                }

                byte[] raw =
                    characteristic.getValue();

                final String response =
                    raw == null
                    ? ""
                    : new String(raw).trim();

                runOnUiThread(
                    new Runnable() {
                        @Override
                        public void run() {

                            if (
                                AUTH_UUID.equals(
                                    characteristicUuid
                                )
                            ) {

                                if ("AUTH_OK".equals(response)) {

                                    statusText.setText(
                                        "Kimlik doğrulama başarılı. "
                                        + "Kurulum oturumu hazırlanıyor..."
                                    );

                                    prepareSession(
                                        gatt
                                    );

                                } else if (
                                    "AUTH_FAILED".equals(response)
                                ) {

                                    statusText.setText(
                                        "Kurulum PIN'i hatalı."
                                    );

                                    stylePrimaryButton(
                                        connectButton,
                                        true
                                    );

                                } else {

                                    statusText.setText(
                                        "AUTH cevabı: "
                                        + response
                                    );
                                }

                                return;
                            }


                            if (
                                SESSION_UUID.equals(
                                    characteristicUuid
                                )
                            ) {

                                if (
                                    "SESSION_ACTIVE=1".equals(
                                        response
                                    )
                                ) {

                                    statusText.setText(
                                        "Kurulum oturumu aktif. "
                                        + "Wi-Fi bilgilerini girin."
                                    );

                                    if (
                                        wifiSetupSection
                                            != null
                                    ) {
                                        wifiSetupSection
                                            .setVisibility(
                                                View.VISIBLE
                                            );
                                    }

                                    setupSessionActive =
                                        true;

                                    if (
                                        bleNextButton != null
                                    ) {
                                        bleNextButton.setEnabled(
                                            true
                                        );

                                        stylePrimaryButton(
                                            bleNextButton,
                                            true
                                        );
                                    }

                                    prepareWifiProvisioning(
                                        gatt
                                    );

                                } else if (
                                    "SESSION_DENIED_AUTH_REQUIRED"
                                        .equals(response)
                                ) {

                                    statusText.setText(
                                        "Kurulum oturumu reddedildi: "
                                        + "kimlik doğrulama gerekli."
                                    );

                                } else if (
                                    "SESSION_DENIED_BUSY"
                                        .equals(response)
                                ) {

                                    statusText.setText(
                                        "Kurulum oturumu meşgul."
                                    );

                                } else {

                                    statusText.setText(
                                        "SESSION cevabı: "
                                        + response
                                    );
                                }

                                return;
                            }


                            if (
                                WIFI_STATUS_UUID.equals(
                                    characteristicUuid
                                )
                            ) {

                                if (
                                    "WIFI_SSID_OK".equals(response)
                                ) {

                                    statusText.setText(
                                        "Wi-Fi adı alındı."
                                    );

                                } else if (
                                    "WIFI_PASSWORD_OK".equals(response)
                                ) {

                                    statusText.setText(
                                        "Wi-Fi şifresi alındı."
                                    );

                                } else if (
                                    "WIFI_CONNECT_QUEUED".equals(response)
                                ) {

                                    statusText.setText(
                                        "Wi-Fi bağlantısı hazırlanıyor..."
                                    );

                                } else if (
                                    "WIFI_CONNECTING".equals(response)
                                ) {

                                    statusText.setText(
                                        "Wi-Fi ağına bağlanılıyor..."
                                    );

                                } else if (
                                    response.startsWith(
                                        "WIFI_CONNECTED="
                                    )
                                ) {

                                    String ip =
                                        response.substring(
                                            "WIFI_CONNECTED=".length()
                                        );

                                    statusText.setText(
                                        "Wi-Fi bağlantısı başarılı. IP: "
                                        + ip
                                    );

                                    setupWifiConnected =
                                        true;

                                    setupWifiSsid =
                                        pendingWifiSsid;

                                    setupWifiIp =
                                        ip;

                                    updateCompleteSummary();

                                    if (
                                        wifiNextButton != null
                                    ) {
                                        wifiNextButton.setEnabled(
                                            true
                                        );

                                        stylePrimaryButton(
                                            wifiNextButton,
                                            true
                                        );
                                    }

                                    pendingWifiPassword =
                                        null;

                                    pendingWifiSsid =
                                        null;

                                    if (
                                        wifiPasswordInput
                                            != null
                                    ) {
                                        wifiPasswordInput
                                            .setText("");
                                    }

                                    wifiConnectButton.setEnabled(
                                        true
                                    );

                                    stylePrimaryButton(
                                        wifiConnectButton,
                                        true
                                    );

                                } else if (
                                    "WIFI_PROVISIONED".equals(response)
                                ) {

                                    statusText.setText(
                                        "Wi-Fi bilgileri kaydedildi."
                                    );

                                } else if (
                                    "WIFI_FAILED".equals(response)
                                ) {

                                    statusText.setText(
                                        "Wi-Fi bağlantısı kurulamadı. "
                                        + "Ağ adı ve şifreyi kontrol edin."
                                    );

                                    setupWifiConnected =
                                        false;

                                    if (
                                        wifiNextButton != null
                                    ) {
                                        wifiNextButton.setEnabled(
                                            false
                                        );

                                        stylePrimaryButton(
                                            wifiNextButton,
                                            false
                                        );
                                    }

                                    pendingWifiPassword =
                                        null;

                                    pendingWifiSsid =
                                        null;

                                    wifiConnectButton.setEnabled(
                                        true
                                    );

                                    stylePrimaryButton(
                                        wifiConnectButton,
                                        true
                                    );

                                } else {

                                    statusText.setText(
                                        "Wi-Fi durumu: "
                                        + response
                                    );
                                }
                            }
                        }
                    }
                );
            }

        };


    private void stopBleScan() {

        if (
            bleScanner != null
            && hasBlePermissions()
        ) {
            try {
                bleScanner.stopScan(
                    scanCallback
                );
            } catch (Exception ignored) {
            }
        }
    }

    private final ScanCallback scanCallback =
        new ScanCallback() {

            @Override
            public void onScanResult(
                int callbackType,
                ScanResult result
            ) {

                if (result == null) {
                    return;
                }

                String deviceName = null;

                /*
                 * 1) Once advertising paketindeki
                 * Complete Local Name alanini dene.
                 */
                try {

                    if (
                        result.getScanRecord()
                            != null
                    ) {

                        deviceName =
                            result
                                .getScanRecord()
                                .getDeviceName();
                    }

                } catch (Exception ignored) {
                }

                /*
                 * 2) Bazi Android cihazlarda ScanRecord
                 * ismi null gelebilir. BluetoothDevice
                 * uzerinden tekrar dene.
                 */
                if (
                    deviceName == null
                    || deviceName.trim().isEmpty()
                ) {

                    try {

                        if (
                            result.getDevice()
                                != null
                        ) {

                            deviceName =
                                result
                                    .getDevice()
                                    .getName();
                        }

                    } catch (Exception ignored) {
                    }
                }

                /*
                 * DEBUG:
                 * Callback'e gelen HER BLE cihazini ekranda goster.
                 */
                String displayName = deviceName;

                if (
                    displayName == null
                    || displayName.trim().isEmpty()
                ) {

                    try {

                        if (
                            result.getDevice()
                                != null
                        ) {

                            displayName =
                                result
                                    .getDevice()
                                    .getAddress();
                        }

                    } catch (Exception ignored) {
                    }
                }

                if (
                    displayName == null
                    || displayName.trim().isEmpty()
                ) {
                    displayName = "Adsiz BLE cihazi";
                }

                statusText.setText(
                    "Bulundu: " + displayName
                );

                deviceText.setText(
                    displayName
                );

                /*
                 * MERALED cihazi ise secilebilir yap.
                 */
                if (
                    deviceName != null
                    && deviceName.startsWith(
                        "MERALED-"
                    )
                ) {

                    foundDeviceName =
                        deviceName;

                    foundDevice =
                        result.getDevice();

                    stopBleScan();

                    deviceText.setText(
                        "✓ " + deviceName
                    );

                    statusText.setText(
                        "Durum: MERALED cihazı bulundu."
                    );

                    scanButton.setEnabled(true);
                    scanButton.setText(
                        "TEKRAR TARA"
                    );

                    stylePrimaryButton(
                        connectButton,
                        true
                    );
                }
            }

            @Override
            public void onScanFailed(
                int errorCode
            ) {

                stylePrimaryButton(
                    scanButton,
                    true
                );

                scanButton.setText(
                    "TEKRAR TARA"
                );

                statusText.setText(
                    "BLE tarama başarısız. Kod: "
                    + errorCode
                );
            }
        };

    @Override
    public void onRequestPermissionsResult(
        int requestCode,
        String[] permissions,
        int[] grantResults
    ) {

        super.onRequestPermissionsResult(
            requestCode,
            permissions,
            grantResults
        );

        if (
            requestCode
                == BLE_PERMISSION_REQUEST
        ) {

            if (hasBlePermissions()) {

                statusText.setText(
                    "Bluetooth izni verildi."
                );

                startBleScan();

            } else {

                statusText.setText(
                    "Bluetooth izni verilmedi. "
                    + "Kurulum yapılamaz."
                );
            }
        }
    }

    private int dp(int value) {

        float density =
            getResources()
                .getDisplayMetrics()
                .density;

        return (int) (
            value * density + 0.5f
        );
    }

    @Override
    protected void onDestroy() {
        stopBleScan();

        if (bluetoothGatt != null) {
            try {
                bluetoothGatt.close();
            } catch (Exception ignored) {
            }

            bluetoothGatt = null;
        }

        super.onDestroy();
    }
}
