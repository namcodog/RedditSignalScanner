/**
 * 登录页面
 *
 * 重定向到首页，登录功能在首页的对话框中实现
 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // 重定向到首页
    navigate('/', { replace: true });
  }, [navigate]);

  return null;
};

export default LoginPage;

