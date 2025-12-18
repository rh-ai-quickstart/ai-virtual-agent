import { createFileRoute, Outlet } from '@tanstack/react-router';
import { useCurrentUser } from '@/contexts/UserContext';
import { useEffect } from 'react';

const backendUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:8000';

export const Route = createFileRoute('/_protected')({
  component: ProtectedPages,
});

function ProtectedPages() {
  const { currentUser, isLoading, error } = useCurrentUser();

  // Redirect immediately on auth failure
  useEffect(() => {
    if (!isLoading && (error || !currentUser)) {
      window.location.href = `${backendUrl}/auth/login`;
    }
  }, [currentUser, isLoading, error]);

  // Don't render anything if not authenticated
  if (!currentUser) {
    return null;
  }

  return <Outlet />;
}
