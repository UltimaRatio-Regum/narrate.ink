Analyze this voice sample and return your assessment as a single JSON object. Do not include any text outside the JSON. Follow this schema exactly:

```json
{
  "gender": "male | female | androgynous",
  "estimated_age_range": "child | teen | young_adult | adult | middle_aged | senior",
  "pitch": {
    "level": "very_low | low | medium_low | medium | medium_high | high | very_high",
    "description": "<free text, e.g. 'rich bass register' or 'bright upper-mid range'>"
  },
  "accent": {
    "primary": "<most specific identification possible, e.g. 'General American', 'Received Pronunciation', 'Australian General', 'Southern US', 'Dublin Irish', 'Scottish Highlands'>",
    "region_family": "american | british | australian | irish | scottish | south_african | indian | caribbean | canadian | other",
    "non_native_influence": "<null if native speaker, otherwise describe detected L1 influence, e.g. 'French L1 influence' or 'Mandarin L1 influence'>",
    "confidence": "high | medium | low"
  },
  "timbre": {
    "primary_descriptors": ["<pick 2-4 from: warm, bright, dark, nasal, breathy, gravelly, smooth, raspy, thin, full, rich, reedy, husky, crisp, mellow, metallic, velvety, hollow, piercing, round>"],
    "description": "<1-2 sentence free text characterization of the overall tonal quality>"
  },
  "vocal_qualities": {
    "breathiness": "none | slight | moderate | heavy",
    "nasality": "none | slight | moderate | heavy",
    "raspiness": "none | slight | moderate | heavy",
    "vocal_fry": "none | slight | moderate | heavy",
    "sibilance": "none | slight | moderate | heavy"
  },
  "pacing": {
    "speaking_rate": "very_slow | slow | moderate | fast | very_fast",
    "rhythm": "steady | varied | staccato | flowing | halting"
  },
  "energy": {
    "level": "subdued | calm | moderate | animated | intense",
    "emotional_tone": "<e.g. 'authoritative and measured', 'friendly and conversational', 'dramatic and expressive', 'neutral and clinical'>"
  },
  "clarity": {
    "articulation": "mumbled | casual | clear | crisp | over_enunciated",
    "intelligibility": "low | moderate | high | very_high"
  },
  "recording_quality": {
    "noise_level": "clean | slight_noise | moderate_noise | noisy",
    "room_sound": "dry_studio | slight_reverb | moderate_reverb | echoey",
    "overall_quality": "professional | good | acceptable | poor",
    "notes": "<any issues: clipping, compression artifacts, background music, etc. null if none>"
  },
  "casting_tags": ["<3-6 freeform tags describing what this voice would be cast as, e.g. 'narrator', 'villain', 'news anchor', 'warm grandmother', 'action hero', 'audiobook literary fiction', 'podcast host', 'fairy tale storyteller'>"],
  "suggested_display_name": "<a short evocative name for this voice in a voice picker UI, e.g. 'Oxford Scholar', 'Texas Storyteller', 'Velvet Baritone', 'Brooklyn Edge'>",
  "summary": "<2-3 sentence overall description suitable for displaying alongside the voice in a selection UI>"
}
```

### Field guidance

- **gender**: Base this on vocal characteristics, not assumptions. Use "androgynous" if genuinely ambiguous.
- **accent.primary**: Be as geographically specific as the sample allows. "American" alone is too vague if you can narrow it further.
- **timbre.primary_descriptors**: Pick the 2-4 most dominant qualities. Order them by prominence.
- **casting_tags**: Think about what kinds of characters, narration styles, or content genres this voice suits. These will be used for searchable filtering.
- **suggested_display_name**: Make it memorable and evocative. It should help a user quickly recall which voice this is.
- **recording_quality**: This helps flag samples that might need re-recording or cleanup before use in cloning.
- **summary**: Write this as if it's the blurb a user reads when hovering over a voice option. Be concise but vivid.

### Important

- Return ONLY the JSON object. No markdown fencing, no preamble, no commentary.
- If a field is genuinely indeterminate from the sample, use `null` rather than guessing.
- If the audio contains multiple speakers, analyze only the dominant/primary voice.