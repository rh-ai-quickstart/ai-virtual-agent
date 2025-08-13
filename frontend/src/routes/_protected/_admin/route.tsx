import { createFileRoute, Outlet, Link } from '@tanstack/react-router';
import { useCurrentUser } from '@/contexts/UserContext';

export const Route = createFileRoute('/_protected/_admin')({
  component: AdminPages,
});

function AdminPages() {
  const { currentUser, isLoading } = useCurrentUser();

  // Loading is handled by parent _protected route, but add fallback
  if (isLoading) {
    return <div>Loading...</div>;
  }

  // Check admin role - currentUser should exist due to _protected parent route
  if (!currentUser || currentUser.role !== 'admin') {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h2>Access Denied</h2>
        <p>You need administrator privileges to access this page.</p>
        <p>Your current role: {currentUser?.role || 'None'}</p>
        <Link
          to="/"
          style={{
            padding: '10px 20px',
            backgroundColor: '#007bff',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '4px',
            display: 'inline-block',
            marginTop: '10px',
          }}
        >
          Go to Chat
        </Link>
      </div>
    );
  }

  return <Outlet />;
}
