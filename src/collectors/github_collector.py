#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GitHub采集器

采集GitHub Trending上的AI相关项目。
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from src.collectors.base_collector import BaseCollector, CollectorError
from src.config import Config, get_config

logger = logging.getLogger(__name__)


class GithubCollector(BaseCollector):
    """
    GitHub Trending采集器

    采集GitHub Trending上的AI相关项目。
    注意：GitHub Trending没有公开API，需要爬取网页。
    """

    BASE_URL = "https://github.com"
    TRENDING_URL = "https://github.com/trending"

    # AI相关语言
    AI_LANGUAGES = ["Python", "Jupyter Notebook", "C++", "TypeScript", "Go"]

    def __init__(self, config: Optional[Config] = None, source_id: str = "github_trending_ai"):
        super().__init__(config, source_id)

        # 获取GitHub Token（如果有）
        self.headers = {}
        if self.config.github_token:
            self.headers["Authorization"] = f"token {self.config.github_token}"

    async def collect(self, since: str = "daily") -> List[Dict[str, Any]]:
        """
        采集GitHub Trending项目

        Args:
            since: 时间范围 (daily, weekly, monthly)

        Returns:
            项目列表
        """
        logger.info(f"开始采集GitHub Trending，时间范围: {since}")

        all_projects = []

        # 遍历AI相关语言
        for language in self.AI_LANGUAGES:
            try:
                projects = await self._collect_by_language(language, since)
                all_projects.extend(projects)
                logger.info(f"{language} 采集到 {len(projects)} 个项目")
            except Exception as e:
                logger.error(f"采集 {language} 失败: {e}")

        # 过滤AI相关项目
        ai_projects = [p for p in all_projects if self._is_ai_related(p)]
        logger.info(f"过滤后AI相关项目: {len(ai_projects)}/{len(all_projects)}")

        return ai_projects

    async def _collect_by_language(self, language: str, since: str) -> List[Dict[str, Any]]:
        """按语言采集Trending项目"""
        params = {
            "since": since,
            "l": language,
        }
        url = f"{self.TRENDING_URL}?{urlencode(params)}"

        try:
            response_text = await self._fetch(url, headers=self.headers)
            if not response_text:
                return []

            return self._parse_trending_page(response_text, language)

        except Exception as e:
            logger.error(f"采集 {language} Trending失败: {e}")
            return []

    def _parse_trending_page(self, html: str, language: str) -> List[Dict[str, Any]]:
        """解析Trending页面"""
        soup = BeautifulSoup(html, "lxml")
        projects = []

        # 查找所有项目条目
        articles = soup.select("article.Box-row")

        for article in articles:
            try:
                project = self._parse_project_article(article, language)
                if project:
                    projects.append(project)
            except Exception as e:
                logger.warning(f"解析项目条目失败: {e}")
                continue

        return projects

    def _parse_project_article(self, article, language: str) -> Optional[Dict[str, Any]]:
        """解析单个项目条目"""
        # 获取项目链接和名称
        title_elem = article.select_one("h2 a")
        if not title_elem:
            return None

        href = title_elem.get("href", "")
        repo_name = href.strip("/").split("/")[-2:]
        if len(repo_name) != 2:
            return None

        owner, name = repo_name
        url = f"{self.BASE_URL}{href}"

        # 获取描述
        desc_elem = article.select_one("p")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # 获取编程语言
        lang_elem = article.select_one("span[itemprop='programmingLanguage']")
        prog_language = lang_elem.get_text(strip=True) if lang_elem else language

        # 获取星标数
        stars_elem = article.select_one("a[href$='/stargazers']")
        stars = self._parse_number(stars_elem.get_text(strip=True)) if stars_elem else 0

        # 获取fork数
        forks_elem = article.select_one("a[href$='/forks']")
        forks = self._parse_number(forks_elem.get_text(strip=True)) if forks_elem else 0

        # 获取今日星标数（如果有的话）
        today_stars = 0
        # 查找包含小绿色三角形的span元素（代表star增长）
        star_growth_elem = article.select_one("svg.octicon-arrow-small-down, svg.octicon-arrow-small-up, .hx_color-icon-success")
        if star_growth_elem:
            parent = star_growth_elem.parent
            if parent:
                # 查找包含数值的文本
                for child in parent.descendants:
                    if hasattr(child, 'string') and child.string:
                        text = child.string.strip()
                        if text and any(c.isdigit() for c in text):
                            today_stars = self._parse_number(text)
                            break

        # 备选方案：寻找可能包含增量的其他元素
        if today_stars == 0:
            # 尝试查找包含"stars today"或类似文字的元素
            all_spans = article.find_all(['span', 'div'])
            for span_elem in all_spans:
                span_text = span_elem.get_text(strip=True).lower()
                if 'today' in span_text or 'stars' in span_text:
                    # 提取数字
                    import re
                    numbers = re.findall(r'\d+', span_text)
                    if numbers:
                        today_stars = int(numbers[0])
                        break

        return {
            "url": url,
            "title": f"{owner}/{name}",
            "description": description,
            "published_at": datetime.now().isoformat(),  # GitHub没有明确的发布时间
            "source": "GitHub",
            "category": "tools",
            "author": owner,
            "language": prog_language,
            "stars": stars,
            "forks": forks,
            "today_stars": today_stars,
            "tags": [prog_language, "github", "open-source"],
            "score": today_stars * 10 + stars,  # 热度评分
        }

    def _parse_number(self, text: str) -> int:
        """解析数字（支持K, M等单位）"""
        text = text.strip().replace(",", "")

        multipliers = {
            "k": 1000,
            "m": 1000000,
            "b": 1000000000,
        }

        for suffix, mult in multipliers.items():
            if text.lower().endswith(suffix):
                try:
                    return int(float(text[:-1]) * mult)
                except ValueError:
                    return 0

        try:
            return int(text)
        except ValueError:
            return 0

    def _is_ai_related(self, project: Dict[str, Any]) -> bool:
        """检查项目是否与AI相关"""
        config = get_config()
        keywords = config.keywords.get_all_keywords()

        # 检查标题和描述
        text = f"{project.get('title', '')} {project.get('description', '')}".lower()

        # 检查关键词匹配
        for keyword in keywords:
            if keyword.lower() in text:
                return True

        # 检查topic标签（如果有）
        return False


class GithubReleaseCollector(BaseCollector):
    """
    GitHub Release采集器

    采集指定AI框架的Release更新。
    """

    # 重要的AI项目
    AI_PROJECTS = [
        "openai/openai-python",
        "langchain-ai/langchain",
        "microsoft/semantic-kernel",
        "run-llama/llama_index",
        "deepset-ai/haystack",
        "vllm-project/vllm",
        "lm-sys/FastChat",
    ]

    BASE_URL = "https://api.github.com"

    def __init__(self, config: Optional[Config] = None, source_id: str = "github_releases"):
        super().__init__(config, source_id)

        # GitHub API需要认证
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.config.github_token:
            self.headers["Authorization"] = f"token {self.config.github_token}"

    async def collect(self, hours: int = 168) -> List[Dict[str, Any]]:
        """采集GitHub Release"""
        logger.info("开始采集GitHub Release")

        all_releases = []

        for project in self.AI_PROJECTS:
            try:
                releases = await self._get_project_releases(project, hours)
                all_releases.extend(releases)
            except Exception as e:
                logger.error(f"采集 {project} Release失败: {e}")

        logger.info(f"GitHub Release采集完成，获得 {len(all_releases)} 个更新")
        return all_releases

    async def _get_project_releases(self, project: str, hours: int) -> List[Dict[str, Any]]:
        """获取项目Release"""
        url = f"{self.BASE_URL}/repos/{project}/releases"

        try:
            response_text = await self._fetch(url, headers=self.headers)
            if not response_text:
                return []

            import json
            releases = json.loads(response_text)

            result = []
            for release in releases[:5]:  # 只取最近5个
                try:
                    article = self._parse_release(release, project, hours)
                    if article:
                        result.append(article)
                except Exception as e:
                    logger.warning(f"解析Release失败: {e}")
                    continue

            return result

        except Exception as e:
            logger.error(f"获取 {project} Release失败: {e}")
            return []

    def _parse_release(self, release: Dict[str, Any], project: str, hours: int) -> Optional[Dict[str, Any]]:
        """解析Release"""
        published = release.get("published_at", "")

        if not self._is_within_time_window(published, hours):
            return None

        name = release.get("name", "")
        tag_name = release.get("tag_name", "")
        body = release.get("body", "")
        html_url = release.get("html_url", "")

        # 清理body（移除emoji和多余空格）
        clean_body = self._clean_release_body(body)

        return {
            "url": html_url,
            "title": f"{project} {tag_name}",
            "description": clean_body[:1000],
            "published_at": published,
            "source": "GitHub",
            "category": "tools",
            "author": project.split("/")[0],
            "tags": ["release", "github", "update"],
            "score": 0,
        }

    def _clean_release_body(self, body: str) -> str:
        """清理Release内容"""
        if not body:
            return ""

        # 移除emoji（简单处理）
        import re
        body = re.sub(r":[a-z_]+:", "", body)

        # 移除多余空格
        body = re.sub(r"\s+", " ", body).strip()

        return body[:500]  # 限制长度
