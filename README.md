<!-- ──────────────────────────────────────────────────────────────── -->
# 🌱 Sustainable Investment Toolkit
> **지속가능 투자(Sustainable Investment)**·경제 분석을 위한 100 % 오픈소스 파이썬 프로젝트  
<!-- ──────────────────────────────────────────────────────────────── -->

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9‒3.12-blue.svg)](https://www.python.org/)
[![Build](https://github.com/your-username/sustainable-investment/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/sustainable-investment/actions)
[![Docs](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://your-username.github.io/sustainable-investment)

> *“Balance profit **and** purpose—one pull request at a time.”*

---

## 📑 개요
**Sustainable Investment Toolkit**은 ESG·임팩트·기후 리스크 데이터를  
*프로그래머블* 방식으로 수집·분석·시각화하여 **데이터 기반 지속가능 투자 전략**을 연구합니다.  

- **오직 파이썬**으로 작성 → Windows에서도 바로 실행  
- Jupyter Notebook, Dash 대시보드, 백테스트 스크립트를 모두 포함  
- “발표 지연·데이터 누수” 방지용 **Point-in-Time** 레이어 내장  

---

## 📚 목차
1. [주요 특징](#-주요-특징)  
2. [빠른 시작](#-빠른-시작)  
3. [디렉터리 구조](#-디렉터리-구조)  
4. [데이터 소스](#-데이터-소스)  
5. [5분 ESG 백테스트](#-5분-esg-백테스트)  
6. [로드맵](#-로드맵)  
7. [기여 가이드](#-기여-가이드)  
8. [라이선스](#-라이선스)  
9. [연락처](#-연락처)  

---

## ✨ 주요 특징
| 카테고리 | 기능 | 구현 스택 |
|----------|------|-----------|
| **데이터 수집** | Refinitiv·Sustainalytics·SEC 공시 API 래퍼 | `requests`, `pydantic` |
| **누수 방지** | 발표일+지연(Lag) 시프트, Point-in-Time 스냅샷 | `pandas`, `duckdb` |
| **리스크 모델** | CAPM·Fama-French·Carhart 확장팩 | `statsmodels` |
| **백테스트** | 벡터화·병렬 실행 파이프라인 | `vectorbt`, `numba` |
| **대시보드** | 실시간 포트폴리오&시나리오 뷰어 | `Plotly Dash` |
| **문서화** | Sphinx + GitHub Pages 자동 배포 | `sphinx-awesome-theme` |

---

## 🚀 빠른 시작
> **환경** | Windows 10/11, PowerShell, Python 3.9 이상

```powershell
# 1) 저장소 클론
git clone https://github.com/your-username/sustainable-investment.git
cd sustainable-investment

# 2) 가상환경 생성 & 활성화
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # (Cmd.exe 사용 시 .\.venv\Scripts\activate.bat)

# 3) 패키지 설치
pip install -r requirements.txt

# 4) 첫 파이프라인 실행 (2018‒2025 ESG 백테스트)
python scripts\run_pipeline.py --start 2018-01-01 --end 2025-07-31
