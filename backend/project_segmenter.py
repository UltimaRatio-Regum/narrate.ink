import uuid
import re
import json
import logging
import os
import threading
from typing import Optional, List

import httpx

from database import (
    get_db_session, Project, ProjectChapter, ProjectSection, ProjectChunk
)
from text_parser import TextParser

logger = logging.getLogger(__name__)

SECTION_WORD_LIMIT = 300
MAX_CHUNKS_PER_SECTION = 30
WORDS_PER_SECOND = 2.5

text_parser = TextParser()


def split_into_sections(raw_text: str, word_limit: int = SECTION_WORD_LIMIT) -> list[str]:
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]

    if len(paragraphs) <= 1:
        single_newline = [p.strip() for p in raw_text.split("\n") if p.strip()]
        if len(single_newline) > 1:
            paragraphs = single_newline

    if len(paragraphs) <= 1 and raw_text.strip():
        sentences = re.split(r'(?<=[.!?])\s+', raw_text.strip())
        if len(sentences) > 1:
            paragraphs = sentences

    if not paragraphs:
        return [raw_text] if raw_text.strip() else []

    sections: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > word_limit and current:
            sections.append("\n\n".join(current))
            current = [para]
            current_words = para_words
        else:
            current.append(para)
            current_words += para_words

    if current:
        sections.append("\n\n".join(current))

    return sections


def _split_section_by_chunk_count(db, section, max_chunks: int = MAX_CHUNKS_PER_SECTION):
    chunks = db.query(ProjectChunk).filter(
        ProjectChunk.section_id == section.id
    ).order_by(ProjectChunk.chunk_index).all()

    if len(chunks) <= max_chunks:
        return [section]

    new_sections = []
    chunk_groups = []
    for i in range(0, len(chunks), max_chunks):
        chunk_groups.append(chunks[i:i + max_chunks])

    new_sections.append(section)

    base_section_index = section.section_index

    for group_idx, group in enumerate(chunk_groups[1:], start=1):
        new_section = ProjectSection(
            id=str(uuid.uuid4()),
            chapter_id=section.chapter_id,
            section_index=base_section_index + group_idx,
            status="segmented",
        )
        db.add(new_section)
        db.flush()

        for chunk in group:
            chunk.section_id = new_section.id

        new_sections.append(new_section)

    db.commit()
    return new_sections


def _reindex_sections(db, chapter_id: str):
    sections = db.query(ProjectSection).filter(
        ProjectSection.chapter_id == chapter_id
    ).order_by(ProjectSection.section_index, ProjectSection.created_at).all()

    for idx, section in enumerate(sections):
        section.section_index = idx
    db.commit()


def _generate_section_titles(db, chapter_id: str):
    base_url = os.environ.get("AI_INTEGRATIONS_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    api_key = os.environ.get("AI_INTEGRATIONS_OPENROUTER_API_KEY", "")

    if not api_key:
        logger.info("OpenRouter not configured, skipping section title generation")
        return

    sections = db.query(ProjectSection).filter(
        ProjectSection.chapter_id == chapter_id,
        ProjectSection.status == "segmented"
    ).order_by(ProjectSection.section_index).all()

    if not sections:
        return

    section_previews = []
    for sec in sections:
        chunks = db.query(ProjectChunk).filter(
            ProjectChunk.section_id == sec.id
        ).order_by(ProjectChunk.chunk_index).all()

        words = []
        for chunk in chunks:
            words.extend(chunk.text.split())
            if len(words) >= 100:
                break
        preview = " ".join(words[:100])
        section_previews.append(f"Section {sec.section_index + 1}: {preview}")

    prompt = (
        "You are summarizing sections of a book chapter for an audiobook project.\n"
        "For each section below, write an extremely brief summary (5-8 words max) "
        "describing what happens. Use present tense. Be specific about characters and events.\n"
        "Return a JSON array of strings, one title per section, in order.\n\n"
        + "\n\n".join(section_previews)
    )

    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "openai/gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

        titles = parsed if isinstance(parsed, list) else parsed.get("titles", parsed.get("sections", []))

        if not isinstance(titles, list):
            logger.warning("LLM returned unexpected format for section titles")
            return

        for i, sec in enumerate(sections):
            if i < len(titles) and titles[i]:
                sec.title = str(titles[i])[:200]

        db.commit()
        logger.info(f"Generated {len(titles)} section titles for chapter {chapter_id}")

    except Exception as e:
        logger.warning(f"Failed to generate section titles: {e}")


def segment_project_background(project_id: str, use_llm: bool = False):
    thread = threading.Thread(
        target=_run_segmentation,
        args=(project_id, use_llm),
        daemon=True
    )
    thread.start()
    return thread


def _run_segmentation(project_id: str, use_llm: bool = False):
    db = get_db_session()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            logger.error(f"Project {project_id} not found")
            return

        project.status = "segmenting"
        db.commit()

        chapters = db.query(ProjectChapter).filter(
            ProjectChapter.project_id == project_id
        ).order_by(ProjectChapter.chapter_index).all()

        all_known_speakers: list[str] = []

        for chapter in chapters:
            try:
                chapter.status = "segmenting"
                db.commit()

                section_texts = split_into_sections(chapter.raw_text)
                chunk_global_index = 0

                all_chapter_sections = []

                for sec_idx, section_text in enumerate(section_texts):
                    section = ProjectSection(
                        id=str(uuid.uuid4()),
                        chapter_id=chapter.id,
                        section_index=sec_idx,
                        status="processing",
                    )
                    db.add(section)
                    db.commit()

                    try:
                        segments, detected_speakers = text_parser.parse(
                            section_text, known_speakers=all_known_speakers
                        )
                        for sp in detected_speakers:
                            if sp and sp not in all_known_speakers:
                                all_known_speakers.append(sp)

                        for seg_idx, seg in enumerate(segments):
                            if hasattr(seg, 'dict'):
                                seg_dict = seg.dict() if hasattr(seg, 'dict') else seg
                            else:
                                seg_dict = seg

                            seg_text = seg_dict.get("text", "") if isinstance(seg_dict, dict) else getattr(seg, "text", "")
                            seg_type = seg_dict.get("type", "narration") if isinstance(seg_dict, dict) else getattr(seg, "type", "narration")
                            seg_speaker = seg_dict.get("speaker") if isinstance(seg_dict, dict) else getattr(seg, "speaker", None)
                            seg_sentiment = seg_dict.get("sentiment") if isinstance(seg_dict, dict) else getattr(seg, "sentiment", None)
                            seg_wc = seg_dict.get("wordCount") if isinstance(seg_dict, dict) else getattr(seg, "wordCount", None)

                            wc = seg_wc or len(seg_text.split())
                            emotion = "neutral"
                            if seg_sentiment:
                                if isinstance(seg_sentiment, dict):
                                    emotion = seg_sentiment.get("label", "neutral")
                                elif hasattr(seg_sentiment, "label"):
                                    emotion = seg_sentiment.label

                            chunk = ProjectChunk(
                                id=str(uuid.uuid4()),
                                section_id=section.id,
                                chunk_index=chunk_global_index,
                                text=seg_text,
                                segment_type=seg_type,
                                speaker=seg_speaker,
                                emotion=emotion,
                                word_count=wc,
                                approx_duration_seconds=round(wc / WORDS_PER_SECOND, 1),
                            )
                            db.add(chunk)
                            chunk_global_index += 1

                        section.status = "segmented"
                        db.commit()

                        result_sections = _split_section_by_chunk_count(db, section)
                        all_chapter_sections.extend(result_sections)

                    except Exception as e:
                        logger.error(f"Failed to segment section {sec_idx} of chapter {chapter.chapter_index}: {e}")
                        section.status = "failed"
                        section.error_message = str(e)
                        db.commit()
                        all_chapter_sections.append(section)

                _reindex_sections(db, chapter.id)

                if use_llm:
                    try:
                        _generate_section_titles(db, chapter.id)
                    except Exception as e:
                        logger.warning(f"Section title generation failed for chapter {chapter.chapter_index}: {e}")

                if all_known_speakers:
                    chapter.speakers_json = json.dumps(all_known_speakers)

                chapter.status = "segmented"
                db.commit()

            except Exception as e:
                logger.error(f"Failed to segment chapter {chapter.chapter_index}: {e}")
                chapter.status = "failed"
                chapter.error_message = str(e)
                db.commit()

        failed_chapters = db.query(ProjectChapter).filter(
            ProjectChapter.project_id == project_id,
            ProjectChapter.status == "failed"
        ).count()

        if failed_chapters == len(chapters):
            project.status = "failed"
            project.error_message = "All chapters failed to segment"
        else:
            project.status = "segmented"

        if all_known_speakers:
            project.speakers_json = json.dumps(
                {sp: {"name": sp, "voiceSampleId": None, "pitchOffset": 0, "speedFactor": 1.0}
                 for sp in all_known_speakers}
            )

        db.commit()
        logger.info(f"Project {project_id} segmentation complete: {project.status}")

    except Exception as e:
        logger.error(f"Project segmentation failed: {e}")
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "failed"
                project.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
