import { createFileRoute, Outlet } from '@tanstack/react-router';
import { useCurrentUser } from '@/contexts/UserContext';

export const Route = createFileRoute('/_protected')({
  component: ProtectedPages,
});

function ProtectedPages() {
  const { currentUser, isLoading, error } = useCurrentUser();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error || !currentUser) {
    const params = new URLSearchParams(window.location.search);
    if (params.has('error')) {
      return (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h2>Authentication Failed</h2>
          <p>Unable to sign in. Please try again or contact your administrator.</p>
          <a href="/api/v1/auth/login">Try again</a>
        </div>
      );
    }

    const key = '_auth_redirect_count';
    const count = parseInt(sessionStorage.getItem(key) || '0', 10);
    if (count >= 3) {
      sessionStorage.removeItem(key);
      return (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h2>Authentication Failed</h2>
          <p>
            Unable to establish a session. Check that cookies are enabled and the site is served
            over HTTPS.
          </p>
          <a href="/api/v1/auth/login">Try again</a>
        </div>
      );
    }
    sessionStorage.setItem(key, String(count + 1));
    window.location.href = '/api/v1/auth/login';

    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h2>Redirecting to Login...</h2>
        <p>Please wait while we redirect you to the login page.</p>
      </div>
    );
  }

  sessionStorage.removeItem('_auth_redirect_count');
  return <Outlet />;
}
