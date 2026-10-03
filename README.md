# 酒类产品库云端采集项目

这个项目在 GitHub Actions 云服务器上运行，不使用本地浏览器。它读取 `inputs/` 中的 8 份品牌清单，生成品牌清洗审计表，然后按品类并行查询公开数据源、下载公开可访问的产品图片，最终生成 `alcohol_products.csv` 和图片文件夹。

每个品类还会生成 `brand_verification_<category>.csv`。只有检索到对应品类产品的品牌才标记为 `verified_has_category_product`；没有公开证据、来源报错和疑似 OCR 条目会分开保留，避免把跨品类品牌误当成有效品牌。

## 数据字段

`name, brand, alcohol_type_name, sub_type_name, abv, volume_ml, origin, image_filename, product_url, image_source_url, source_name, data_status, is_discontinued_or_limited`

CSV 使用 UTF-8 BOM 编码，可直接用 Excel 打开。相同产品的不同容量保持为不同记录。

## 使用方法

1. 在 GitHub 新建一个仓库。
2. 将本项目全部文件上传到仓库根目录。
3. 打开仓库的 **Actions** 页面，启用工作流。
4. 选择 **Collect alcohol catalogue**，点击 **Run workflow**。
5. 运行结束后，在该次任务的 **Artifacts** 下载 `alcohol-catalog-complete`。

默认每月 1 日自动更新一次，也可以只保留手动运行。首次运行可能持续数小时；8 个品类会并行采集。

## 品牌清洗

`brands_cleaning.csv` 保留原始名称、规范名、英文别名、输入文件和行号。明显 OCR 粘连或乱码标记为 `needs_review`，不会静默删除。自动核验无法证明的品牌或历史产品会标记为 `review_needed`，而不是伪装成已确认数据。

## 数据来源和边界

当前无密钥来源包括 Open Food Facts 与 Wikidata。程序只访问公开页面，并保存产品页和图片来源 URL。开放数据库无法保证覆盖全球全部停产、私人装瓶和限定产品；“完整”应理解为公开来源能够检索和核验的记录集合。

如需显著提高历史产品覆盖率，可以后续增加获得授权的数据源或搜索 API。请先确认相应网站的服务条款及图片再分发许可。

## 本地测试（可选）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest
alcohol-catalog clean-brands
alcohol-catalog collect --category whisky --pages 1
```
