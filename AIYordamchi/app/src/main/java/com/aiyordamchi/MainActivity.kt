package com.aiyordamchi

import android.annotation.SuppressLint
import android.graphics.Color
import android.os.Bundle
import android.view.Window
import android.view.WindowManager
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Full screen, no title
        requestWindowFeature(Window.FEATURE_NO_TITLE)
        supportActionBar?.hide()

        // Status bar color
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
        window.statusBarColor = Color.parseColor("#6B3FA0")

        setContentView(R.layout.activity_main)
        webView = findViewById(R.id.webView)

        setupWebView()
        webView.loadUrl("file:///android_asset/index.html")
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val settings: WebSettings = webView.settings

        // Enable JavaScript
        settings.javaScriptEnabled = true

        // Enable DOM storage (for localStorage)
        settings.domStorageEnabled = true

        // Allow file access
        settings.allowFileAccess = true

        // Enable mixed content (HTTP + HTTPS)
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW

        // Enable viewport meta tag
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true

        // Zoom
        settings.setSupportZoom(false)
        settings.builtInZoomControls = false

        // Cache
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        // Encoding
        settings.defaultTextEncodingName = "UTF-8"

        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, url: String): Boolean {
                // Allow all URLs (needed for Anthropic API calls)
                return false
            }
        }

        webView.setBackgroundColor(Color.WHITE)
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
