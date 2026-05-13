# phase970

## 这轮达到的目的
修复 `miniPoints` 云函数无法在微信开发者工具中创建/部署的问题。

## 当前状态变化
- `miniPoints` 目录已补齐最小部署文件：
  - `config.json`
  - `package.json`
- `miniPoints` 现在和 `miniAuth` / `miniFavorites` 处于同一部署规格。

## 验证结果
- `cd hotpost-mini/hotpost-mini-app && npm run build:weapp`
- 结果：通过

## 下一步做什么
在微信开发者工具里重新上传并部署 `miniPoints`，然后继续部署 `miniAuth` 和 `miniFavorites`，验证首页授权登录不再报函数找不到。
