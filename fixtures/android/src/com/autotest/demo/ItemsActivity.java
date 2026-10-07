package com.autotest.demo;

import android.app.Activity;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.widget.*;
import org.json.*;

public class ItemsActivity extends Activity {
    public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout=new LinearLayout(this);layout.setOrientation(LinearLayout.VERTICAL);layout.setPadding(32,24,32,32);
        ScrollView scroll=new ScrollView(this);scroll.addView(layout);setContentView(scroll);
        TextView title=new TextView(this);title.setText("Saved items");title.setTextSize(26);layout.addView(title);
        TextView data=new TextView(this);data.setContentDescription("Items");layout.addView(data);
        Button back=new Button(this);back.setText("Back to editor");back.setContentDescription("Back to editor");back.setOnClickListener(view->finish());layout.addView(back);
        SharedPreferences preferences=getSharedPreferences("fixture",MODE_PRIVATE);
        new Thread(() -> {
            try {
                JSONObject response=MainActivity.request(preferences.getString("base","http://10.0.2.2:8765"),"/api/items","GET",null,preferences.getString("authorization",null));
                JSONArray items=response.getJSONArray("items");StringBuilder text=new StringBuilder();
                for(int i=0;i<items.length();i++){JSONObject item=items.getJSONObject(i);text.append(item.getString("name")).append(" × ").append(item.getInt("quantity")).append("\n");}
                runOnUiThread(() -> data.setText(text.toString().trim()));
            } catch(Exception error){runOnUiThread(() -> data.setText("Could not load items. Check network."));}
        }).start();
    }
}
