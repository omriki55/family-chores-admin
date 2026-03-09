import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from "@/context/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Shield, Chrome, Lock } from "lucide-react";

export default function LoginPage() {
  const { user, isAdmin, loading, signIn, signInWithPassword, passwordAuth } = useAuthContext();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [passwordError, setPasswordError] = useState(false);

  useEffect(() => {
    if (!loading && (passwordAuth || (user && isAdmin))) navigate("/", { replace: true });
  }, [user, isAdmin, loading, navigate, passwordAuth]);

  const handlePasswordLogin = async () => {
    setPasswordError(false);
    const ok = await signInWithPassword(password);
    if (!ok) {
      setPasswordError(true);
      setPassword("");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/5 via-background to-primary/10 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto h-16 w-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
            <Shield className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl">Admin Panel</CardTitle>
          <CardDescription>
            MyHappyFam — Family Management Dashboard
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
            </div>
          ) : user && !isAdmin ? (
            <div className="text-center space-y-3">
              <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm">
                <p className="font-medium">Access Denied</p>
                <p className="text-xs mt-1">{user.email} is not an admin</p>
              </div>
              <Button variant="outline" onClick={() => window.location.reload()}>
                Try Different Account
              </Button>
            </div>
          ) : (
            <>
              {/* Password login */}
              <div className="space-y-2">
                <div className="flex gap-2">
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setPasswordError(false); }}
                    onKeyDown={(e) => e.key === "Enter" && handlePasswordLogin()}
                    placeholder="הזן סיסמה..."
                    className="flex-1 h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                  <Button onClick={handlePasswordLogin} size="default">
                    <Lock className="h-4 w-4 mr-1" />
                    כניסה
                  </Button>
                </div>
                {passwordError && (
                  <p className="text-xs text-destructive text-center">סיסמה שגויה</p>
                )}
              </div>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-background px-2 text-muted-foreground">או</span>
                </div>
              </div>

              {/* Google login */}
              <Button onClick={signIn} className="w-full" size="lg" variant="outline">
                <Chrome className="h-5 w-5 mr-2" />
                Sign in with Google
              </Button>
            </>
          )}
          <p className="text-xs text-center text-muted-foreground">
            Only authorized administrators can access this panel
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
