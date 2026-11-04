// DroidDesk | Creator: David o Baiano Maligno | Co-author: Nexo
import java.io.ByteArrayOutputStream;
import java.lang.reflect.*;
import java.util.*;

/** Read-only metadata collector. Runs as adb shell via app_process; no APK install. */
public final class DroidDeskMetadata {
    static Object call(Object o, String n, Class<?>[] t, Object... a) throws Exception {
        Method m = o.getClass().getMethod(n, t);
        m.setAccessible(true);
        return m.invoke(o, a);
    }
    static Object field(Object o, String n) throws Exception { return o.getClass().getField(n).get(o); }
    static String quote(Object value) {
        String s = String.valueOf(value);
        StringBuilder b = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '"' || c == '\\') b.append('\\').append(c);
            else if (c == '\n') b.append("\\n");
            else if (c == '\r') b.append("\\r");
            else if (c == '\t') b.append("\\t");
            else if (c < 32) b.append(String.format("\\u%04x", (int)c));
            else b.append(c);
        }
        return b.append('"').toString();
    }
    static String icon(Object info, Object pm, Class<?> pmType) {
        try {
            // Read the static resource directly. Samsung loadIcon() executes
            // live-calendar code that expects a normal app/zygote font setup.
            int resource = ((Integer)field(info,"icon")).intValue();
            Object drawable;
            if (resource == 0) {
                drawable = call(pm,"getDefaultActivityIcon",new Class<?>[]{});
            } else {
                Object resources = call(pm,"getResourcesForApplication",new Class<?>[]{Class.forName("android.content.pm.ApplicationInfo")},info);
                drawable = call(resources,"getDrawable",new Class<?>[]{int.class,Class.forName("android.content.res.Resources$Theme")},resource,null);
            }
            Class<?> bitmapType = Class.forName("android.graphics.Bitmap");
            Class<?> configType = Class.forName("android.graphics.Bitmap$Config");
            Object config = configType.getField("ARGB_8888").get(null);
            Object bitmap = bitmapType.getMethod("createBitmap", int.class, int.class, configType).invoke(null, 64, 64, config);
            Class<?> canvasType = Class.forName("android.graphics.Canvas");
            Object canvas = canvasType.getConstructor(bitmapType).newInstance(bitmap);
            call(drawable, "setBounds", new Class<?>[]{int.class,int.class,int.class,int.class}, 0,0,64,64);
            call(drawable, "draw", new Class<?>[]{canvasType}, canvas);
            Class<?> formatType = Class.forName("android.graphics.Bitmap$CompressFormat");
            Object png = formatType.getField("PNG").get(null);
            ByteArrayOutputStream stream = new ByteArrayOutputStream();
            bitmapType.getMethod("compress",formatType,int.class,java.io.OutputStream.class).invoke(bitmap,png,100,stream);
            bitmapType.getMethod("recycle").invoke(bitmap);
            return Base64.getEncoder().encodeToString(stream.toByteArray());
        } catch (Throwable e) { return ""; }
    }
    public static void main(String[] args) throws Exception {
        Class.forName("android.os.Looper").getMethod("prepareMainLooper").invoke(null);
        Class<?> at = Class.forName("android.app.ActivityThread");
        Method systemMain = at.getDeclaredMethod("systemMain");
        systemMain.setAccessible(true);
        Object thread = systemMain.invoke(null);
        Method getContext = at.getDeclaredMethod("getSystemContext");
        getContext.setAccessible(true);
        Object context = getContext.invoke(thread);
        int user = args.length > 0 ? Integer.parseInt(args[0]) : 0;
        if (user != 0) {
            Class<?> userType = Class.forName("android.os.UserHandle");
            Object handle = userType.getMethod("of",int.class).invoke(null,user);
            context = call(context,"createContextAsUser",new Class<?>[]{userType,int.class},handle,0);
        }
        Object pm = call(context,"getPackageManager",new Class<?>[]{});
        Class<?> pmType = Class.forName("android.content.pm.PackageManager");
        List<?> apps = (List<?>)call(pm,"getInstalledApplications",new Class<?>[]{int.class}, 0x00002000 | 0x00000200 | 0x00008000);
        for (Object info : apps) {
            try {
                String pkg = (String)field(info,"packageName");
                String label = String.valueOf(call(info,"loadLabel",new Class<?>[]{pmType},pm));
                Object pi = call(pm,"getPackageInfo",new Class<?>[]{String.class,int.class},pkg,0x00002000 | 0x00000200 | 0x00008000);
                Object version = field(pi,"versionName");
                long apkBytes = new java.io.File((String)field(info,"sourceDir")).length();
                Object splitFiles = field(info,"splitSourceDirs");
                if (splitFiles != null) for (String path : (String[])splitFiles) apkBytes += new java.io.File(path).length();
                String row = "{\"package\":" + quote(pkg) + ",\"label\":" + quote(label)
                    + ",\"version\":" + quote(version == null ? "" : version)
                    + ",\"uid\":" + field(info,"uid") + ",\"target_sdk\":" + field(info,"targetSdkVersion")
                    + ",\"apk_bytes\":" + apkBytes
                    + ",\"source\":" + quote(field(info,"sourceDir"))
                    + ",\"icon\":" + quote(icon(info,pm,pmType)) + "}";
                System.out.println(row);
            } catch (Throwable e) {
                System.err.println("metadata: " + e.toString());
            }
        }
        System.out.flush();
        System.exit(0);
    }
}
