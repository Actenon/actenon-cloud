import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppShell, RootErrorBoundary } from './components/AppShell';
import { TrustSurface } from './screens/TrustSurface';
import { ReviewQueue } from './screens/ReviewQueue';
import { ActionLedger } from './screens/ActionLedger';
import { Styleguide } from './screens/Styleguide';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const router = createBrowserRouter([
  {
    path: '/app',
    element: <AppShell />,
    errorElement: <RootErrorBoundary />,
    children: [
      { index: true, element: <TrustSurface /> },
      { path: 'actions/:id', element: <TrustSurface /> },
      { path: 'review', element: <ReviewQueue /> },
      { path: 'ledger', element: <ActionLedger /> },
      { path: 'styleguide', element: <Styleguide /> },
    ],
  },
]);

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}
