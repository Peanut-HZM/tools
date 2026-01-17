/**
 * Auth Guard Component - Protects routes that require authentication
 */
import { ReactNode, useState, useCallback } from 'react';
import { useAuth } from '../../stores/authStore';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';

interface AuthGuardProps {
  children: ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading, clearError } = useAuth();
  const [showRegister, setShowRegister] = useState(false);

  const handleSwitchToRegister = useCallback(() => {
    clearError();
    setShowRegister(true);
  }, [clearError]);

  const handleSwitchToLogin = useCallback(() => {
    clearError();
    setShowRegister(false);
  }, [clearError]);

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500 mx-auto mb-4"></div>
          <p className="text-slate-400">验证登录状态...</p>
        </div>
      </div>
    );
  }

  // Show login/register form if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
        {showRegister ? (
          <RegisterForm
            onSuccess={() => {}}
            onSwitchToLogin={handleSwitchToLogin}
          />
        ) : (
          <LoginForm
            onSuccess={() => {}}
            onSwitchToRegister={handleSwitchToRegister}
          />
        )}
      </div>
    );
  }

  // Render protected content
  return <>{children}</>;
}
