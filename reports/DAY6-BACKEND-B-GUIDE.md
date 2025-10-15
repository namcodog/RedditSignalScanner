# Day 6 Backend B 开发指南

> **角色**: Backend Agent B (中级后端)
> **日期**: 2025-10-12 (Day 6)
> **核心任务**: 认证系统集成 + 任务系统稳定性验证
> **预计用时**: 7小时

---

## 🎯 今日目标

1. ✅ 认证系统与API全面集成
2. ✅ 完善认证系统文档
3. ✅ Celery任务系统稳定性测试
4. ✅ 任务监控接口开发
5. ✅ MyPy --strict 0 errors

---

## 📋 详细任务清单

### 上午任务 (9:00-12:00)

#### ✅ 任务1: 认证系统API集成测试 (9:00-10:30, 1.5小时)

**目标**: 验证JWT认证已正确集成到所有API端点

**执行步骤**:

```bash
# 1. 创建认证集成测试文件
touch backend/tests/api/test_auth_integration.py

# 2. 编写完整的集成测试
```

**完整测试代码**:

```python
# backend/tests/api/test_auth_integration.py
"""
认证系统API集成测试
验证所有API端点都正确集成JWT认证
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import get_password_hash


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """创建测试用户"""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("SecurePass123")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user2(db_session: AsyncSession) -> User:
    """创建第二个测试用户"""
    user = User(
        email="test2@example.com",
        password_hash=get_password_hash("SecurePass456")
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_token(client: AsyncClient, test_user: User) -> str:
    """获取有效的认证Token"""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "test@example.com",
            "password": "SecurePass123"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def auth_token_user2(client: AsyncClient, test_user2: User) -> str:
    """获取第二个用户的Token"""
    response = await client.post(
        "/api/auth/login",
        json={
            "email": "test2@example.com",
            "password": "SecurePass456"
        }
    )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestAuthenticationRequired:
    """测试API端点需要认证"""

    @pytest.mark.asyncio
    async def test_analyze_requires_auth(self, client: AsyncClient):
        """测试POST /api/analyze需要认证"""
        response = await client.post(
            "/api/analyze",
            json={"product_description": "测试产品描述" * 3}
        )
        assert response.status_code == 401
        assert "not authenticated" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_status_requires_auth(self, client: AsyncClient):
        """测试GET /api/status/{task_id}需要认证"""
        task_id = "00000000-0000-0000-0000-000000000001"
        response = await client.get(f"/api/status/{task_id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_report_requires_auth(self, client: AsyncClient):
        """测试GET /api/report/{task_id}需要认证"""
        task_id = "00000000-0000-0000-0000-000000000001"
        response = await client.get(f"/api/report/{task_id}")
        assert response.status_code == 401


class TestValidTokenAccess:
    """测试有效Token的API访问"""

    @pytest.mark.asyncio
    async def test_analyze_with_valid_token(
        self,
        client: AsyncClient,
        auth_token: str
    ):
        """测试带有效Token的分析请求"""
        response = await client.post(
            "/api/analyze",
            json={"product_description": "AI笔记应用测试产品描述" * 3},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "status" in data

    @pytest.mark.asyncio
    async def test_status_with_valid_token(
        self,
        client: AsyncClient,
        auth_token: str
    ):
        """测试带有效Token的状态查询"""
        # 先创建任务
        create_response = await client.post(
            "/api/analyze",
            json={"product_description": "测试状态查询的产品描述" * 3},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        task_id = create_response.json()["task_id"]

        # 查询状态
        response = await client.get(
            f"/api/status/{task_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert response.json()["task_id"] == task_id


class TestInvalidTokenHandling:
    """测试无效Token处理"""

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, client: AsyncClient):
        """测试无效Token格式"""
        response = await client.post(
            "/api/analyze",
            json={"product_description": "测试产品" * 5},
            headers={"Authorization": "Bearer invalid_token_format"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix(self, client: AsyncClient):
        """测试缺少Bearer前缀"""
        response = await client.post(
            "/api/analyze",
            json={"product_description": "测试产品" * 5},
            headers={"Authorization": "some_token"}
        )
        assert response.status_code == 401


class TestMultiTenantIsolation:
    """测试多租户数据隔离"""

    @pytest.mark.asyncio
    async def test_cross_tenant_access_denied(
        self,
        client: AsyncClient,
        auth_token: str,
        auth_token_user2: str
    ):
        """测试跨租户访问被拒绝"""
        # User1创建任务
        response1 = await client.post(
            "/api/analyze",
            json={"product_description": "User1的产品描述测试内容" * 3},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        task_id = response1.json()["task_id"]

        # User2尝试访问User1的任务
        response2 = await client.get(
            f"/api/status/{task_id}",
            headers={"Authorization": f"Bearer {auth_token_user2}"}
        )

        # 应该返回403 Forbidden
        assert response2.status_code == 403
        assert "not authorized" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_own_task_access_allowed(
        self,
        client: AsyncClient,
        auth_token: str
    ):
        """测试访问自己的任务被允许"""
        # 创建任务
        response1 = await client.post(
            "/api/analyze",
            json={"product_description": "测试自己的任务访问权限" * 3},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        task_id = response1.json()["task_id"]

        # 访问自己的任务
        response2 = await client.get(
            f"/api/status/{task_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # 应该成功
        assert response2.status_code == 200
        assert response2.json()["task_id"] == task_id
```

**运行测试**:

```bash
# 运行认证集成测试
pytest backend/tests/api/test_auth_integration.py -v

# 期望输出:
# test_auth_integration.py::TestAuthenticationRequired::test_analyze_requires_auth PASSED
# test_auth_integration.py::TestAuthenticationRequired::test_status_requires_auth PASSED
# test_auth_integration.py::TestAuthenticationRequired::test_report_requires_auth PASSED
# test_auth_integration.py::TestValidTokenAccess::test_analyze_with_valid_token PASSED
# test_auth_integration.py::TestValidTokenAccess::test_status_with_valid_token PASSED
# test_auth_integration.py::TestInvalidTokenHandling::test_invalid_token_format PASSED
# test_auth_integration.py::TestInvalidTokenHandling::test_missing_bearer_prefix PASSED
# test_auth_integration.py::TestMultiTenantIsolation::test_cross_tenant_access_denied PASSED
# test_auth_integration.py::TestMultiTenantIsolation::test_own_task_access_allowed PASSED
# ==================== 9 passed in 3.45s ====================
```

**验收标准**:
- [ ] 所有API端点都需要认证
- [ ] 无效Token返回401
- [ ] 跨租户访问返回403
- [ ] 测试9/9通过

---

#### ✅ 任务2: 完善认证系统文档 (10:30-12:00, 1.5小时)

**目标**: 更新AUTH_SYSTEM_DESIGN.md,补充详细的使用指南

**执行步骤**:

```bash
# 编辑认证系统设计文档
vi backend/docs/AUTH_SYSTEM_DESIGN.md
```

**完整文档内容** (追加到现有文档):

```markdown
# 认证系统设计文档

> **创建日期**: 2025-10-11
> **最后更新**: 2025-10-12
> **版本**: v2.0

---

## Token刷新策略 (新增)

### 短期Token设计

**设计原则**:
- 访问Token有效期: 30分钟
- 刷新Token有效期: 7天
- Token刷新端点: `POST /api/auth/refresh`

### Token刷新流程

```
客户端 (检测Token即将过期)
    ↓
调用 POST /api/auth/refresh
    ↓ (发送refresh_token)
服务器验证refresh_token
    ↓
生成新的access_token + refresh_token
    ↓
返回TokenResponse
    ↓
客户端更新本地存储
```

### 实现代码

```python
# backend/app/api/routes/auth.py (新增)
@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="刷新访问Token"
)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    """
    刷新访问Token

    Args:
        refresh_token: 刷新Token

    Returns:
        TokenResponse: 新的access_token和refresh_token

    Raises:
        401: refresh_token无效或过期
    """
    try:
        # 解码refresh_token
        payload = jwt.decode(
            refresh_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )

        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )

        # 验证用户存在
        user = await db.get(User, user_id)
        if user is None:
            raise HTTPException(
                status_code=401,
                detail="User not found"
            )

        # 生成新的access_token和refresh_token
        new_access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=30)
        )

        new_refresh_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(days=7)
        )

        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            refresh_token=new_refresh_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                created_at=user.created_at
            )
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Refresh token has expired. Please login again."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )
```

### 安全措施

1. **Refresh Token Rotation**
   - 每次刷新都生成新的refresh_token
   - 旧的refresh_token立即失效

2. **重放攻击检测**
   - 检测refresh_token是否已被使用
   - 维护已使用Token的黑名单

3. **Token黑名单机制**
   - 用户登出时Token加入黑名单
   - 黑名单存储在Redis (TTL = Token有效期)

---

## API认证使用指南 (新增)

### 前端集成完整示例

```typescript
// frontend/src/services/auth.service.ts

import axios, { AxiosInstance } from 'axios';

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    created_at: string;
  };
}

class AuthService {
  private apiClient: AxiosInstance;

  constructor() {
    this.apiClient = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL,
    });

    // 请求拦截器: 自动添加Token
    this.apiClient.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // 响应拦截器: 自动刷新Token
    this.apiClient.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // 如果是401错误且未重试过
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            // 尝试刷新Token
            const refreshToken = localStorage.getItem('refresh_token');
            if (!refreshToken) {
              throw new Error('No refresh token');
            }

            const response = await axios.post<TokenResponse>(
              `${import.meta.env.VITE_API_BASE_URL}/api/auth/refresh`,
              { refresh_token: refreshToken }
            );

            const { access_token, refresh_token: newRefreshToken } = response.data;

            // 更新本地存储
            localStorage.setItem('auth_token', access_token);
            localStorage.setItem('refresh_token', newRefreshToken);

            // 更新原请求的Authorization header
            originalRequest.headers.Authorization = `Bearer ${access_token}`;

            // 重试原请求
            return this.apiClient.request(originalRequest);
          } catch (refreshError) {
            // 刷新失败,清除Token并跳转登录
            localStorage.removeItem('auth_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const response = await this.apiClient.post<TokenResponse>(
      '/api/auth/login',
      { email, password }
    );

    // 存储Token
    localStorage.setItem('auth_token', response.data.access_token);
    localStorage.setItem('refresh_token', response.data.refresh_token);

    return response.data;
  }

  async logout(): Promise<void> {
    // 清除本地Token
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');

    // TODO: 调用后端登出接口,将Token加入黑名单
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('auth_token');
  }
}

export const authService = new AuthService();
```

### 后端API测试示例

```bash
#!/bin/bash
# backend/scripts/test_auth_flow.sh
# 测试完整认证流程

API_BASE="http://localhost:8000"

echo "=== Reddit Signal Scanner 认证流程测试 ==="
echo ""

# 1. 注册用户
echo "1. 注册新用户..."
REGISTER_RESPONSE=$(curl -s -X POST "$API_BASE/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }')

echo "注册响应: $REGISTER_RESPONSE"
echo ""

# 2. 登录获取Token
echo "2. 登录获取Token..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_BASE/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }')

echo "登录响应: $LOGIN_RESPONSE"

# 提取access_token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token')
REFRESH_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.refresh_token')
echo "Access Token: $ACCESS_TOKEN"
echo ""

# 3. 使用Token调用受保护API
echo "3. 使用Token调用分析API..."
ANALYZE_RESPONSE=$(curl -s -X POST "$API_BASE/api/analyze" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "AI笔记应用测试产品描述,帮助研究者自动组织和连接想法"
  }')

echo "分析响应: $ANALYZE_RESPONSE"
TASK_ID=$(echo "$ANALYZE_RESPONSE" | jq -r '.task_id')
echo ""

# 4. 查询任务状态
echo "4. 查询任务状态..."
STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/api/status/$TASK_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

echo "状态响应: $STATUS_RESPONSE"
echo ""

# 5. 测试Token刷新
echo "5. 测试Token刷新..."
REFRESH_RESPONSE=$(curl -s -X POST "$API_BASE/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{
    \"refresh_token\": \"$REFRESH_TOKEN\"
  }")

echo "刷新响应: $REFRESH_RESPONSE"
NEW_ACCESS_TOKEN=$(echo "$REFRESH_RESPONSE" | jq -r '.access_token')
echo "新Access Token: $NEW_ACCESS_TOKEN"
echo ""

# 6. 测试无Token访问(应该失败)
echo "6. 测试无Token访问(应该返回401)..."
UNAUTHORIZED_RESPONSE=$(curl -s -w "\nHTTP Status: %{http_code}" \
  -X POST "$API_BASE/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "product_description": "测试未授权访问"
  }')

echo "$UNAUTHORIZED_RESPONSE"
echo ""

echo "=== 认证流程测试完成 ==="
```

**运行测试脚本**:

```bash
chmod +x backend/scripts/test_auth_flow.sh
./backend/scripts/test_auth_flow.sh
```

---

## 常见问题与解决方案

### Q1: 前端收到401错误

**原因**:
1. Token过期
2. Token格式错误
3. 用户不存在

**解决方案**:
```typescript
// 检查Token是否存在
const token = localStorage.getItem('auth_token');
if (!token) {
  // 跳转登录页
  window.location.href = '/login';
}

// 检查Authorization header格式
// 正确: "Bearer <token>"
// 错误: "<token>" (缺少Bearer前缀)
```

### Q2: CORS错误

**原因**: Backend CORS配置未包含Frontend域名

**解决方案**:
```python
# backend/app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # React dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Q3: 跨租户数据泄露

**原因**: API端点未检查user_id

**解决方案**:
```python
# 所有需要访问资源的API都要检查
@router.get("/api/status/{task_id}")
async def get_task_status(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    task = await db.get(Task, task_id)

    # 多租户权限检查
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return task
```

---

**文档版本**: v2.0
**最后更新**: 2025-10-12
**维护人**: Backend Agent B
```

**验收标准**:
- [ ] Token刷新策略完整
- [ ] 前端集成示例可运行
- [ ] 测试脚本可执行
- [ ] 常见问题文档清晰

---

### 下午任务 (14:00-18:00)

#### ✅ 任务3: Celery任务系统稳定性测试 (14:00-16:00, 2小时)

**目标**: 全面测试任务系统的可靠性

详细实现请参考 `DAY6-TASK-ASSIGNMENT.md` 中的相关章节。

#### ✅ 任务4: 任务监控接口开发 (16:00-18:00, 2小时)

**目标**: 实现GET /api/tasks/stats监控接口

详细实现请参考 `DAY6-TASK-ASSIGNMENT.md` 中的相关章节。

---

## 📊 今日验收清单

### 功能验收
- [ ] ✅ 认证系统100%集成到API
- [ ] ✅ 多租户数据隔离正确
- [ ] ✅ 任务系统稳定性验证
- [ ] ✅ 任务监控接口实现

### 测试验收
- [ ] ✅ 认证集成测试9/9通过
- [ ] ✅ 任务稳定性测试通过
- [ ] ✅ 监控接口测试通过
- [ ] ✅ MyPy --strict 0 errors

### 文档验收
- [ ] ✅ AUTH_SYSTEM_DESIGN.md更新完成
- [ ] ✅ Token刷新策略文档完整
- [ ] ✅ API使用指南清晰

---

**Day 6 Backend B 加油! 🚀**
