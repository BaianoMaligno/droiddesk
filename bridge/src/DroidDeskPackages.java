// DroidDesk | Creator: David o Baiano Maligno | Co-author: Nexo
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/** Per-user system package removal through the platform interface, as adb shell. */
public final class DroidDeskPackages {
    static Object manager;
    static Method query;
    static boolean longFlags;

    static Object info(String name, int user) throws Exception {
        // Include disabled applications, but never MATCH_UNINSTALLED_PACKAGES.
        Object flags = longFlags ? (Object) Long.valueOf(0x8200) : Integer.valueOf(0x8200);
        return query.invoke(manager, name, flags, user);
    }

    static String quote(String value) {
        StringBuilder out = new StringBuilder("\"");
        for (char c : value.toCharArray()) {
            if (c == '"' || c == '\\') out.append('\\').append(c);
            else if (c < 32) out.append(String.format("\\u%04x", (int)c));
            else out.append(c);
        }
        return out.append('"').toString();
    }

    public static void main(String[] args) {
        try {
            if (args.length != 4 || !(args[0].equals("probe") || args[0].equals("uninstall"))
                    || !args[1].matches("[0-9]+")
                    || !args[2].matches("[a-zA-Z0-9_]+(?:\\.[a-zA-Z0-9_]+)*")
                    || !(args[3].equals("keep") || args[3].equals("clear")))
                throw new IllegalArgumentException("Expected probe|uninstall USER PACKAGE keep|clear");
            int user = Integer.parseInt(args[1]);
            String name = args[2];
            Class<?> activityThread = Class.forName("android.app.ActivityThread");
            manager = activityThread.getMethod("getPackageManager").invoke(null);
            Class<?> api = Class.forName("android.content.pm.IPackageManager");
            try {
                query = api.getMethod("getPackageInfo", String.class, long.class, int.class);
                longFlags = true;
            } catch (NoSuchMethodException olderPlatform) {
                query = api.getMethod("getPackageInfo", String.class, int.class, int.class);
            }
            Method delete = api.getMethod("deletePackageAsUser", String.class, int.class,
                    Class.forName("android.content.pm.IPackageDeleteObserver"), int.class, int.class);
            Object before = info(name, user);
            boolean system = false;
            if (before != null) {
                Object app = before.getClass().getField("applicationInfo").get(before);
                int flags = app.getClass().getField("flags").getInt(app);
                int systemFlag = app.getClass().getField("FLAG_SYSTEM").getInt(null);
                system = (flags & systemFlag) != 0;
            }
            if (args[0].equals("probe")) {
                System.out.println("{\"protocol\":1,\"installed\":" + (before != null)
                        + ",\"system\":" + system + ",\"user\":" + user + "}");
            } else {
                if (before == null || !system)
                    throw new IllegalArgumentException("Expected an installed system package for this user");
                Class<?> pm = Class.forName("android.content.pm.PackageManager");
                int flags = pm.getField("DELETE_SYSTEM_APP").getInt(null);
                if (args[3].equals("keep")) flags |= pm.getField("DELETE_KEEP_DATA").getInt(null);
                // AOSP accepts a null legacy observer and wraps it internally.
                // The operation is asynchronous: verify actual absence below.
                delete.invoke(manager, name, -1, null, user, flags);
                long deadline = System.nanoTime() + 15000000000L;
                while (info(name, user) != null) {
                    if (System.nanoTime() >= deadline)
                        throw new IllegalStateException("Android did not confirm per-user removal within 15s");
                    Thread.sleep(150);
                }
                System.out.println("{\"protocol\":1,\"removed\":true,\"user\":" + user
                        + ",\"package\":" + quote(name) + "}");
            }
            System.exit(0);
        } catch (Throwable error) {
            while (error instanceof InvocationTargetException && error.getCause() != null)
                error = error.getCause();
            System.err.println("Error: DroidDesk package helper: " + error);
            System.exit(1);
        }
    }
}
