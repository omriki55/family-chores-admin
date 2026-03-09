import { useState, useEffect } from "react";
import { type User, signInWithPopup, signInAnonymously, GoogleAuthProvider, signOut as fbSignOut, onAuthStateChanged } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { getAdminConfig, setAdminConfig } from "@/lib/firestore";

const googleProvider = new GoogleAuthProvider();
const ADMIN_PASSWORD = "1234";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [passwordAuth, setPasswordAuth] = useState(false);

  // Check if already authenticated via password in sessionStorage
  useEffect(() => {
    const stored = sessionStorage.getItem("admin_password_auth");
    if (stored === "true") {
      setPasswordAuth(true);
      setIsAdmin(true);
      // Also sign in anonymously for Firestore access
      signInAnonymously(auth).catch(() => {}).finally(() => setLoading(false));
    }
  }, []);

  useEffect(() => {
    // If password auth is active, skip Firebase auth
    if (passwordAuth) return;

    const unsub = onAuthStateChanged(auth, async (u) => {
      setUser(u);
      if (u) {
        setChecking(true);
        try {
          const config = await getAdminConfig();
          if (config && config.adminEmails?.includes(u.email || "")) {
            setIsAdmin(true);
          } else if (!config) {
            // First-time bootstrap: create admin config with current user
            const adminEmail = import.meta.env.VITE_ADMIN_EMAIL || u.email;
            await setAdminConfig({ adminEmails: [adminEmail] });
            if (u.email === adminEmail) setIsAdmin(true);
          } else {
            setIsAdmin(false);
          }
        } catch (e) {
          console.error("Admin check failed:", e);
          // Fallback: check env variable
          const adminEmail = import.meta.env.VITE_ADMIN_EMAIL;
          if (adminEmail && u.email === adminEmail) setIsAdmin(true);
        }
        setChecking(false);
      } else {
        setIsAdmin(false);
      }
      setLoading(false);
    });
    return unsub;
  }, [passwordAuth]);

  const signIn = async () => {
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (e) {
      console.error("Sign-in error:", e);
    }
  };

  const signInWithPassword = async (password: string): Promise<boolean> => {
    if (password === ADMIN_PASSWORD) {
      try {
        // Sign in anonymously so Firestore rules (request.auth != null) are satisfied
        await signInAnonymously(auth);
      } catch (e) {
        console.error("Anonymous sign-in failed:", e);
      }
      setPasswordAuth(true);
      setIsAdmin(true);
      setLoading(false);
      sessionStorage.setItem("admin_password_auth", "true");
      return true;
    }
    return false;
  };

  const signOut = async () => {
    if (passwordAuth) {
      setPasswordAuth(false);
      setIsAdmin(false);
      sessionStorage.removeItem("admin_password_auth");
    } else {
      await fbSignOut(auth);
      setIsAdmin(false);
    }
  };

  return { user, isAdmin, loading: loading || checking, signIn, signInWithPassword, signOut, passwordAuth };
}
