/**
 * 404 页面
 * 
 * 最后更新: 2025-10-10 Day 2
 */

import React from 'react';
import { Link } from 'react-router-dom';

const NotFoundPage: React.FC = () => {
  return (
    <div className="not-found-page">
      <h1>404</h1>
      <p>页面不存在</p>
      <Link to="/">返回首页</Link>
    </div>
  );
};

export default NotFoundPage;

