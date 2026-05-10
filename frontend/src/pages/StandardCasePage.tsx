import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { ROUTES } from '@/router/routes';

const StandardCasePage = () => {
  const navigate = useNavigate();
  const { slug = '' } = useParams();

  useEffect(() => {
    if (!slug) {
      navigate(ROUTES.HOME, { replace: true });
      return;
    }

    navigate(ROUTES.STANDARD_REPORT(slug), { replace: true });
  }, [navigate, slug]);

  return <div className="min-h-screen bg-background" />;
};

export default StandardCasePage;
