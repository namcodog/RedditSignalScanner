import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { isAuthenticated, apiClient } from '@/api';

interface AdminRouteProps {
  children: React.ReactNode;
}

const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const location = useLocation();
  const [status, setStatus] = useState<'loading' | 'authorized' | 'unauthorized' | 'forbidden'>('loading');

  useEffect(() => {
    const checkAdmin = async () => {
      // Layer 1: Check if token exists
      if (!isAuthenticated()) {
        setStatus('unauthorized');
        return;
      }

      // Layer 2: Probe Admin API
      try {
        // We use a specific admin endpoint to verify permissions
        // The result is not important, only the success/failure
        await apiClient.get('/admin/dashboard/stats');
        setStatus('authorized');
      } catch (error: any) {
        console.error('[AdminRoute] Access check failed:', error);
        if (error.status === 401) {
          setStatus('unauthorized');
        } else if (error.status === 403) {
          setStatus('forbidden');
        } else {
            // For other errors (e.g. 500, network), we strictly block access
            // to ensure security.
             setStatus('forbidden');
        }
      }
    };

    checkAdmin();
  }, []);

  if (status === 'loading') {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div style={{
          width: '2rem',
          height: '2rem',
          border: '3px solid #3B82F6',
          borderTopColor: 'transparent',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }}></div>
        <div>Verifying Admin Privileges...</div>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  if (status === 'unauthorized') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (status === 'forbidden') {
    return (
      <div style={{ 
        padding: '2rem', 
        textAlign: 'center',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh'
      }}>
        <h1 style={{ fontSize: '2rem', marginBottom: '1rem' }}>403 Forbidden</h1>
        <p style={{ marginBottom: '2rem', color: '#666' }}>
          You do not have permission to access the Admin Console.
        </p>
        <button 
          onClick={() => window.location.href = '/'}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#3B82F6',
            color: 'white',
            border: 'none',
            borderRadius: '0.25rem',
            cursor: 'pointer'
          }}
        >
          Go Home
        </button>
      </div>
    );
  }

  return <>{children}</>;
};

export default AdminRoute;
