<div align="center">

# RiverTemp-Reconstructor

**基于气温的河流水温模拟与重建工具**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)]()
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-00A2AD)]()
[![scikit-learn](https://img.shields.io/badge/ML-scikit--learn-F7931E?logo=scikitlearn&logoColor=white)]()
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)]()

</div>

---

## 这个软件是做什么的

RiverTemp-Reconstructor 是一个桌面端河流水温模拟软件。它只需要**逐日气温（Ta）和日期**，就能用内置模型计算对应的**逐日水温（Tw）**，并用实测水温对模型进行率定和精度评价。

典型用途：

- **补齐缺失水温序列**——实测水温有缺测时，用气温重建出完整序列
- **模型对比研究**——同一组数据并行跑 5 种模型，按 RMSE / NSE 排序比较优劣
- **机制模型参数率定**——用差分进化算法自动搜索 Air2Stream 等模型的最优参数
- **教学与演示**——图形界面完整呈现从数据导入到结果导出的每一步

## 功能特性

- **数据导入**：读取本地 CSV 或加载内置示例数据，下拉映射时间列、气温列、水温列，实时预览
- **模型训练**：5 种模型可切换；公式面板随模型联动；差分进化自动率定参数；实时显示训练进度
- **精度评价**：RMSE、MAE、R²、NSE 四项指标，训练完成后自动填充
- **多模型比较**：勾选多个已训练模型，生成排序表并自动导出对比图
- **结果可视化**：实测—模拟时间序列、散点拟合、多模型对比、RMSE / NSE 柱状图
- **结果导出**：逐日模拟结果 CSV（UTF-8 BOM，Excel 直接打开不乱码）与图表 PNG

## 内置模型

| 模型 | 类型 | 说明 |
|---|---|---|
| Air2Stream | 机制模型 | 基于气温—水温能量平衡微分方程，5 参数，差分进化率定 |
| Linear Regression | 统计模型 | 气温与水温的线性回归 |
| Seasonal Linear | 统计模型 | 在线性回归基础上引入季节周期项 |
| Teq | 统计模型 | 平衡温度模型，按年积日计算平衡水温 |
| Random Forest | 数据驱动 | 随机森林回归，输入气温与年积日 |

## 界面预览

时间序列拟合：

![时间序列](comparison_timeseries.png)

散点拟合：

![散点](comparison_scatter.png)

模型 RMSE 对比：

![RMSE](comparison_rmse.png)

模型 NSE 对比：

![NSE](comparison_nse.png)

> 另有一份[交互式展示页](showcase/index.html)，完整复刻软件四个标签页，可直接在浏览器里点选体验（无需安装依赖）。

---

## 怎么下载和使用

### 1. 下载

在仓库页面点击绿色 **Code** 按钮 → **Download ZIP**，解压到本地；或者直接克隆：

```bash
git clone https://github.com/liu13754606161-netizen/WaterTemp_App.git
cd WaterTemp_App
```

### 2. 准备环境

安装 **Python 3.11**（安装时勾选 “Add Python to PATH”）：https://www.python.org/downloads/

然后安装依赖：

```bash
pip install -r requirements.txt
```

依赖清单：

```
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
scikit-learn>=1.3.0
matplotlib>=3.7.0
PyQt5>=5.15.0
```

### 3. 启动

**Windows**：双击 `start_desktop.bat`。脚本会自动检查 Python 3.11 和依赖，缺什么就装什么，然后启动程序。

也可以用命令行：

```bash
python app.py
```

### 4. 第一次使用

1. 在「数据导入」页点 **加载内置示例数据**（365 条日尺度记录，站点：一道湾）
2. 确认时间列 `time`、气温列 `Ta`、水温列 `Tw` 的映射，点 **确认列名映射**
3. 在「模型训练」页选择模型，点 **开始训练**；练完会显示四项指标和拟合参数
4. 勾选多个模型点 **模型比较**，结果按 RMSE 排序
5. 到「结果可视化」页查看图表，到「结果导出」页导出 CSV 和 PNG

自己的数据按示例格式准备即可：至少包含时间、气温、水温三列，编码支持 UTF-8 与 GBK。

---

## 项目结构

```
WaterTemp_App/
├── app.py                      主窗口、四个功能页、交互逻辑
├── core.py                     数据读取、序列构建、Air2Stream 模拟、参数率定
├── metrics.py                  RMSE / MAE / R² / NSE
├── model_training.py           训练流程封装
├── model_comparison.py         多模型比较、图表绘制、结果导出
├── models/                     五种模型的公式、参数说明与工厂
│   ├── model_catalog.py
│   ├── model_factory.py
│   ├── air2stream_model.py
│   ├── linear_model.py
│   ├── seasonal_linear_model.py
│   ├── teq_model.py
│   └── randomforest_model.py
├── ui/
│   └── formula_panel.py        公式面板
├── 示例数据.csv                 内置示例数据
├── model_comparison.csv        示例集实测指标
├── comparison_*.png            实测对比图
├── RiverTemp_Random_Forest__[已训练]_series.csv
├── start_desktop.bat           Windows 一键启动
├── clean_cache.bat             缓存清理
├── .streamlit/config.toml
├── requirements.txt
└── showcase/
    └── index.html              交互式展示页
```

## 技术栈

Python 3.11 · PyQt5 · NumPy · Pandas · SciPy · scikit-learn · Matplotlib

## 许可证

仅供学习与研究使用。
