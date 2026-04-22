package com.mobius.app;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.Intent;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayList;
import java.util.List;

public class MobiusAccessibilityService extends AccessibilityService {

    private static MobiusAccessibilityService instance;

    public static MobiusAccessibilityService getInstance() {
        return instance;
    }

    @Override
    public void onServiceConnected() {
        instance = this;
        AccessibilityServiceInfo info = new AccessibilityServiceInfo();
        info.eventTypes = AccessibilityEvent.TYPES_ALL_MASK;
        info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
        info.flags = AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS;
        setServiceInfo(info);
    }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {}

    @Override
    public void onInterrupt() {}

    public String readScreen() {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return "";
        List<String> texts = new ArrayList<>();
        collectText(root, texts);
        return String.join("\n", texts);
    }

    private void collectText(AccessibilityNodeInfo node, List<String> out) {
        if (node == null) return;
        if (node.getText() != null) out.add(node.getText().toString());
        for (int i = 0; i < node.getChildCount(); i++) {
            collectText(node.getChild(i), out);
        }
    }

    public boolean tapElement(String contentDesc) {
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return false;
        List<AccessibilityNodeInfo> nodes =
            root.findAccessibilityNodeInfosByText(contentDesc);
        if (!nodes.isEmpty()) {
            return nodes.get(0).performAction(AccessibilityNodeInfo.ACTION_CLICK);
        }
        return false;
    }

    public boolean openApp(String packageName) {
        Intent intent = getPackageManager().getLaunchIntentForPackage(packageName);
        if (intent == null) return false;
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        startActivity(intent);
        return true;
    }
}
