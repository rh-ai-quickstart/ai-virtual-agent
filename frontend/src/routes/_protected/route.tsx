import { createFileRoute, Outlet } from '@tanstack/react-router'
import { useCurrentUser } from '@/contexts/UserContext'

export const Route = createFileRoute('/_protected')({
    component: ProtectedPages,
})

function ProtectedPages() {
    const { currentUser, isLoading, error } = useCurrentUser()

    // Show loading state
    if (isLoading) {
        return <div>Loading...</div>
    }

    // If no user or authentication error, redirect to OAuth login
    if (error || !currentUser) {
        // Redirect to OAuth login with current URL as return path
        const currentUrl = window.location.href
        const redirectUrl = `/oauth/sign_in?redirect=${encodeURIComponent(currentUrl)}`
        window.location.href = redirectUrl

        // Show a loading message while redirecting
        return (
            <div style={{ padding: '20px', textAlign: 'center' }}>
                <h2>Redirecting to Login...</h2>
                <p>Please wait while we redirect you to the login page.</p>
            </div>
        )
    }

    // User is authenticated, render protected content
    return <Outlet />
}
