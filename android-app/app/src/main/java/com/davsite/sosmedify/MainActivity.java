package com.davsite.sosmedify;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.JavascriptInterface;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.widget.Toast;

import androidx.activity.OnBackPressedCallback;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import androidx.webkit.WebViewAssetLoader;

public class MainActivity extends AppCompatActivity {

    public static final String EMBEDDED_APP_URL = "https://appassets.androidplatform.net/assets/web/index.html";

    private WebView webView;
    private SwipeRefreshLayout swipeRefreshLayout;
    private ProgressBar progressBar;
    private String targetUrl;
    private WebViewAssetLoader assetLoader;
    private boolean isDoubleBackToExitPressedOnce = false;

    // File chooser callback untuk upload file jika diperlukan
    private ValueCallback<Uri[]> filePathCallback;
    private ActivityResultLauncher<Intent> fileChooserLauncher;
    private ActivityResultLauncher<String> requestPermissionLauncher;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // Ambil URL target (default ke aset lokal yang tertanam di dalam APK)
        targetUrl = getString(R.string.web_url);

        // Inisialisasi WebViewAssetLoader untuk melayani aset Frontend lokal (React 19) langsung dari APK
        assetLoader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        webView = findViewById(R.id.webView);
        swipeRefreshLayout = findViewById(R.id.swipeRefreshLayout);
        progressBar = findViewById(R.id.progressBar);

        setupPermissionLauncher();
        setupFileChooserLauncher();
        setupSwipeRefresh();
        setupWebView();
        setupBackNavigation();

        // Muat halaman awal
        loadTargetUrl();
    }

    private void setupPermissionLauncher() {
        requestPermissionLauncher = registerForActivityResult(
                new ActivityResultContracts.RequestPermission(),
                isGranted -> {
                    // Penanganan callback izin jika diperlukan
                }
        );

        // Minta izin notifikasi untuk Android 13+ agar notifikasi unduhan muncul
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) 
                    != PackageManager.PERMISSION_GRANTED) {
                requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS);
            }
        }
    }

    private void setupFileChooserLauncher() {
        fileChooserLauncher = registerForActivityResult(
                new ActivityResultContracts.StartActivityForResult(),
                result -> {
                    if (filePathCallback != null) {
                        Uri[] results = null;
                        if (result.getResultCode() == RESULT_OK && result.getData() != null) {
                            String dataString = result.getData().getDataString();
                            if (dataString != null) {
                                results = new Uri[]{Uri.parse(dataString)};
                            }
                        }
                        filePathCallback.onReceiveValue(results);
                        filePathCallback = null;
                    }
                }
        );
    }

    private void setupSwipeRefresh() {
        swipeRefreshLayout.setColorSchemeColors(
                ContextCompat.getColor(this, R.color.primary),
                ContextCompat.getColor(this, R.color.accent)
        );
        swipeRefreshLayout.setProgressBackgroundColorSchemeColor(
                ContextCompat.getColor(this, R.color.surface)
        );

        swipeRefreshLayout.setOnRefreshListener(() -> {
            if (isNetworkAvailable()) {
                String current = webView.getUrl();
                if (current != null && current.contains("offline.html")) {
                    webView.loadUrl(targetUrl);
                } else {
                    webView.reload();
                }
            } else {
                showOfflinePage();
                swipeRefreshLayout.setRefreshing(false);
            }
        });
    }

    @SuppressLint({"SetJavaScriptEnabled", "JavascriptInterface"})
    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        
        // Identifikasi User Agent aplikasi Sosmedify
        String customUA = settings.getUserAgentString() + " SosmedifyApp/1.0";
        settings.setUserAgentString(customUA);

        // Cookie manager untuk session login jika ada
        CookieManager.getInstance().setAcceptCookie(true);
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true);

        // Bridge Javascript untuk tombol "Coba Lagi" di halaman offline
        webView.addJavascriptInterface(new WebAppInterface(this), "SosmedifyApp");

        // Download Listener untuk video MP4 dan audio MP3
        webView.setDownloadListener((url, userAgent, contentDisposition, mimetype, contentLength) -> {
            startNativeDownload(url, userAgent, contentDisposition, mimetype);
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                // Intersepsi dan layani aset frontend lokal dari assets/web/
                WebResourceResponse response = assetLoader.shouldInterceptRequest(request.getUrl());
                if (response != null) {
                    return response;
                }
                return super.shouldInterceptRequest(view, request);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();

                // Biarkan aset internal aplikasi dan komunikasi API tetap berada di dalam WebView
                if (url.startsWith("https://appassets.androidplatform.net/")
                        || url.contains("up.railway.app")
                        || url.contains("/api/")) {
                    return false;
                }

                // Buka skema khusus atau tautan eksternal di aplikasi lain / browser perangkat
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, request.getUrl());
                    startActivity(intent);
                    return true;
                } catch (Exception e) {
                    return false;
                }
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                progressBar.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                progressBar.setVisibility(View.GONE);
                swipeRefreshLayout.setRefreshing(false);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request.isForMainFrame()) {
                    showOfflinePage();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                if (newProgress >= 100) {
                    progressBar.setVisibility(View.GONE);
                }
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback,
                                              FileChooserParams fileChooserParams) {
                if (MainActivity.this.filePathCallback != null) {
                    MainActivity.this.filePathCallback.onReceiveValue(null);
                }
                MainActivity.this.filePathCallback = filePathCallback;

                Intent intent = fileChooserParams.createIntent();
                try {
                    fileChooserLauncher.launch(intent);
                } catch (Exception e) {
                    MainActivity.this.filePathCallback = null;
                    return false;
                }
                return true;
            }
        });
    }

    private void loadTargetUrl() {
        // Muat aset frontend yang tertanam secara lokal di dalam APK (Tanpa memuat web live eksternal)
        webView.loadUrl(EMBEDDED_APP_URL);
    }

    private void showOfflinePage() {
        webView.loadUrl("https://appassets.androidplatform.net/assets/offline.html");
    }

    /**
     * Download Listener Native menggunakan Android DownloadManager.
     * Mengunduh video / MP3 langsung ke folder Downloads perangkat pengguna.
     */
    private void startNativeDownload(String url, String userAgent, String contentDisposition, String mimetype) {
        try {
            DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
            
            // Nama file otomatis
            String filename = URLUtil.guessFileName(url, contentDisposition, mimetype);
            if (filename == null || filename.isEmpty() || filename.equals("downloadfile.bin")) {
                if (url.contains(".mp3")) {
                    filename = "kliprava_audio_" + System.currentTimeMillis() + ".mp3";
                } else {
                    filename = "kliprava_video_" + System.currentTimeMillis() + ".mp4";
                }
            }

            request.setMimeType(mimetype);
            String cookies = CookieManager.getInstance().getCookie(url);
            request.addRequestHeader("cookie", cookies);
            request.addRequestHeader("User-Agent", userAgent);
            request.setDescription(getString(R.string.download_started));
            request.setTitle(filename);
            request.allowScanningByMediaScanner();
            request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, filename);

            DownloadManager dm = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
            if (dm != null) {
                dm.enqueue(request);
                Toast.makeText(this, getString(R.string.download_started) + " (" + filename + ")", Toast.LENGTH_LONG).show();
            }
        } catch (Exception e) {
            // Fallback: Jika URL blob atau intent, coba buka lewat browser
            try {
                Intent i = new Intent(Intent.ACTION_VIEW);
                i.setData(Uri.parse(url));
                startActivity(i);
            } catch (Exception ex) {
                Toast.makeText(this, "Gagal mengunduh: " + e.getMessage(), Toast.LENGTH_SHORT).show();
            }
        }
    }

    private void setupBackNavigation() {
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack();
                } else {
                    if (isDoubleBackToExitPressedOnce) {
                        setEnabled(false);
                        getOnBackPressedDispatcher().onBackPressed();
                        return;
                    }

                    isDoubleBackToExitPressedOnce = true;
                    Toast.makeText(MainActivity.this, "Tekan sekali lagi untuk keluar", Toast.LENGTH_SHORT).show();

                    new Handler(Looper.getMainLooper()).postDelayed(() -> 
                        isDoubleBackToExitPressedOnce = false, 2000);
                }
            }
        });
    }

    private boolean isNetworkAvailable() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm == null) return false;

        NetworkCapabilities capabilities = cm.getNetworkCapabilities(cm.getActiveNetwork());
        return capabilities != null && (
                capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ||
                capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
        );
    }

    /**
     * Interface untuk interaksi dari Javascript (offline.html)
     */
    public class WebAppInterface {
        Context context;

        WebAppInterface(Context c) {
            context = c;
        }

        @JavascriptInterface
        public void retry() {
            runOnUiThread(() -> {
                loadTargetUrl();
            });
        }
    }
}
