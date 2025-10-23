#!/usr/bin/env node
/**
 * 生成 TypeScript API 客户端
 * 
 * 从 OpenAPI schema 生成类型安全的 API 客户端代码
 * 
 * 用法:
 *   npm run generate:api
 */

import { generate } from 'openapi-typescript-codegen';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const projectRoot = join(__dirname, '..');
const backendRoot = join(projectRoot, '..', 'backend');
const schemaPath = join(backendRoot, 'docs', 'openapi-schema.json');
const outputDir = join(projectRoot, 'src', 'api', 'generated');

console.log('=' .repeat(80));
console.log('🔧 生成 TypeScript API 客户端');
console.log('='.repeat(80));
console.log();

// 检查 schema 文件是否存在
if (!existsSync(schemaPath)) {
  console.error(`❌ OpenAPI schema 文件不存在: ${schemaPath}`);
  console.error();
  console.error('💡 请先生成 schema:');
  console.error('   cd backend && python scripts/update_baseline_schema.py');
  process.exit(1);
}

console.log(`📂 Schema 路径: ${schemaPath}`);
console.log(`📂 输出目录: ${outputDir}`);
console.log();

console.log('🚀 开始生成...');
console.log();

try {
  await generate({
    input: schemaPath,
    output: outputDir,
    httpClient: 'axios',
    useOptions: true,
    useUnionTypes: true,
    exportCore: true,
    exportServices: true,
    exportModels: true,
    exportSchemas: false,
  });

  console.log('✅ TypeScript API 客户端生成成功！');
  console.log();
  console.log('📊 生成的文件:');
  console.log(`   ${outputDir}/`);
  console.log('   ├── core/       # 核心 HTTP 客户端');
  console.log('   ├── models/     # TypeScript 类型定义');
  console.log('   └── services/   # API 服务方法');
  console.log();
  console.log('💡 使用示例:');
  console.log('   import { AnalyzeService } from "@/api/generated";');
  console.log('   const result = await AnalyzeService.createAnalysisTask({ ... });');
  console.log();
} catch (error) {
  console.error('❌ 生成失败:', error.message);
  process.exit(1);
}

