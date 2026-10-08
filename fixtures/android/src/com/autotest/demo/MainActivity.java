package com.autotest.demo;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.text.InputType;
import android.widget.*;
import org.json.*;
import java.net.*;
import java.io.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Local fixture only; uses synthetic credentials and a configurable emulator API endpoint. */
public class MainActivity extends Activity {
    EditText base, user, password, name, quantity;
    TextView status;
    SharedPreferences preferences;
    AtomicBoolean saving = new AtomicBoolean(false);
    boolean defects;

    public void onCreate(Bundle state) {
        super.onCreate(state);
        preferences = getSharedPreferences("fixture", MODE_PRIVATE);
        defects = getIntent().getBooleanExtra("defects", false);
        ScrollView scroll = new ScrollView(this);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(32, 24, 32, 32);
        scroll.addView(layout); setContentView(scroll);
        TextView title = new TextView(this); title.setText("Autotest Demo"); title.setTextSize(26); layout.addView(title);
        base = field(layout, "API URL", preferences.getString("base", "http://10.0.2.2:8765"), InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_URI);
        user = field(layout, "User", "alice", InputType.TYPE_CLASS_TEXT);
        password = field(layout, "Password", "demo-password", InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        button(layout,"Sign in",() -> login());
        name = field(layout,"Name","",InputType.TYPE_CLASS_TEXT);
        quantity = field(layout,"Quantity","1",InputType.TYPE_CLASS_NUMBER);
        button(layout,"Save",() -> save());
        button(layout,"View items",() -> {
            preferences.edit().putString("base",base.getText().toString()).apply();
            Intent intent=new Intent(this,ItemsActivity.class); startActivity(intent);
        });
        button(layout,"Check admin access",() -> admin());
        button(layout,"Sign out",() -> logout());
        button(layout,"Request microphone",() -> requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},7));
        status=new TextView(this);status.setContentDescription("Status");status.setTextSize(17);layout.addView(status);
        status.setText(preferences.contains("authorization")?"Session restored":"Please sign in");
    }

    EditText field(LinearLayout layout,String label,String value,int type) {
        TextView text=new TextView(this);text.setText(label);layout.addView(text);
        EditText field=new EditText(this);field.setContentDescription(label);field.setSingleLine(true);
        field.setInputType(type);field.setText(value);layout.addView(field);return field;
    }
    void button(LinearLayout layout,String label,Runnable action) {
        Button button=new Button(this);button.setText(label);button.setContentDescription(label);
        button.setOnClickListener(view -> action.run());layout.addView(button);
    }
    void show(String text){runOnUiThread(() -> status.setText(text));}

    void login() {
        final String address=base.getText().toString(), username=user.getText().toString(), secret=password.getText().toString();
        show("Signing in");
        new Thread(() -> {
            try {
                JSONObject body=new JSONObject().put("username",username).put("password",secret);
                JSONObject result=request(address,"/api/login","POST",body,null);
                preferences.edit().putString("base",address).putString("authorization",result.getString("authorization")).apply();
                show("Signed in as "+result.getString("username"));
            } catch(Exception error){show("Sign in failed. Check credentials or network.");}
        }).start();
    }
    void save() {
        final String item=name.getText().toString().trim(),address=base.getText().toString();
        final int count;
        try {count=Integer.parseInt(quantity.getText().toString());}
        catch(Exception error){show("Quantity must be between 1 and 100");return;}
        if(item.length()==0||item.length()>100){show("Name must contain 1 to 100 characters");return;}
        if(count<1||count>100){show("Quantity must be between 1 and 100");return;}
        if(!preferences.contains("authorization")){show("Please sign in");return;}
        if(!saving.compareAndSet(false,true))return;
        show("Saving");
        new Thread(() -> {
            try {
                int delay=getIntent().getIntExtra("transport_delay_ms",0);
                if(delay>0)Thread.sleep(Math.min(delay,10000));
                if(!defects)request(address,"/api/items","POST",new JSONObject().put("name",item).put("quantity",count),preferences.getString("authorization",null));
                preferences.edit().putString("base",address).apply();
                show("Saved");
            } catch(HttpFailure error){
                if(error.code==401){preferences.edit().remove("authorization").apply();show("Session expired. Sign in again.");}
                else show("Could not save. Check network and try again.");
            } catch(Exception error){show("Could not save. Check network and try again.");}
            finally{saving.set(false);}
        }).start();
    }
    void admin() {
        final String address=base.getText().toString(),auth=preferences.getString("authorization",null);
        new Thread(() -> {
            try {request(address,"/api/admin","GET",null,auth);show("Admin allowed");}
            catch(HttpFailure error){show(error.code==403?"Admin denied":error.code==401?"Please sign in":"Admin unavailable");}
            catch(Exception error){show("Admin unavailable");}
        }).start();
    }
    void logout() {
        final String address=base.getText().toString(),auth=preferences.getString("authorization",null);
        preferences.edit().remove("authorization").apply();
        new Thread(() -> {
            try {request(address,"/api/logout","POST",new JSONObject(),auth);show("Signed out");}
            catch(Exception error){show("Signed out locally; server logout failed.");}
        }).start();
    }
    static class HttpFailure extends IOException {
        final int code;
        HttpFailure(int code){super("HTTP response failed");this.code=code;}
    }
    public void onRequestPermissionsResult(int code,String[] permissions,int[] results) {
        super.onRequestPermissionsResult(code,permissions,results);
        if(code==7)show(results.length>0&&results[0]==PackageManager.PERMISSION_GRANTED?"Microphone allowed":"Permission denied. Basic features still work.");
    }
    static JSONObject request(String base,String path,String method,JSONObject body,String authorization) throws Exception {
        URL url=new URL(base+path);
        if(!"http".equals(url.getProtocol())&&!"https".equals(url.getProtocol()))throw new IOException("Unsupported test URL");
        HttpURLConnection connection=(HttpURLConnection)url.openConnection();
        connection.setInstanceFollowRedirects(false);connection.setConnectTimeout(3000);connection.setReadTimeout(3000);
        connection.setRequestMethod(method);connection.setRequestProperty("Content-Type","application/json");
        if(authorization!=null)connection.setRequestProperty("Authorization",authorization);
        try {
            if(body!=null){connection.setDoOutput(true);try(OutputStream out=connection.getOutputStream()){out.write(body.toString().getBytes("UTF-8"));}}
            int status=connection.getResponseCode();
            if(status<200||status>=300)throw new HttpFailure(status);
            if(status==204)return new JSONObject();
            try(InputStream in=connection.getInputStream();ByteArrayOutputStream out=new ByteArrayOutputStream()) {
                byte[] buffer=new byte[4096];int count;
                while((count=in.read(buffer))!=-1){if(out.size()+count>1000000)throw new IOException("Response too large");out.write(buffer,0,count);}
                return new JSONObject(out.toString("UTF-8"));
            }
        } finally{connection.disconnect();}
    }
}
