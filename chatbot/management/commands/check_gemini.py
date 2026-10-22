"""Diagnose Gemini API key / model problems using the Google Gen AI SDK.

Usage:
    python manage.py check_gemini

Reads GEMINI_API_KEY and GEMINI_MODEL from settings, lists the models the key
can use, then probes chat-capable models with a tiny prompt and reports which
ones actually answer.  No request body or guest data is sent.
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand

# Text-chat candidates, most stable first.
PREFERRED_TEXT_MODELS = [
    'gemini-3.1-flash-lite',
    'gemini-3.1-flash',
    'gemini-2.5-flash-lite',
    'gemini-2.5-flash',
    'gemini-2.0-flash',
]

SKIP_KEYWORDS = (
    'tts', 'image', 'transcribe', 'lyria', 'robotics',
    'computer-use', 'deep-research', 'nano-banana', 'omni',
    'gemma', 'antigravity', 'embedding',
)


def _model_name(model):
    """Normalise ``models/gemini-...`` to ``gemini-...``."""
    return str(getattr(model, 'name', '') or '').split('/')[-1]


def _model_actions(model):
    actions = getattr(model, 'supported_actions', None) or ()
    return tuple(str(action) for action in actions)


def _error_code(exc):
    for attribute in ('code', 'status_code', 'http_status'):
        value = getattr(exc, attribute, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, 'response', None)
    code = getattr(response, 'status_code', None)
    return code if isinstance(code, int) else None


def _error_detail(exc):
    message = getattr(exc, 'message', None) or str(exc)
    return str(message).strip().replace('\n', ' ')[:300]


class Command(BaseCommand):
    help = 'Check Gemini API key validity and probe which text models answer.'

    def handle(self, *args, **options):
        key = str(getattr(settings, 'GEMINI_API_KEY', '') or '').strip()
        model = str(
            getattr(settings, 'GEMINI_MODEL', 'gemini-3.1-flash-lite')
            or 'gemini-3.1-flash-lite'
        ).strip()
        self.stdout.write(f'GEMINI_MODEL = {model}')
        if not key:
            self.stderr.write('GEMINI_API_KEY is empty. Set it in .env first.')
            return
        self.stdout.write(
            f'GEMINI_API_KEY = {key[:4]}...{key[-4:]} ({len(key)} chars)'
        )

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            self.stderr.write(
                'google-genai is not installed. Run: pip install google-genai'
            )
            return

        try:
            client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(timeout=20000),
            )
            models = list(client.models.list(config={'page_size': 200}))
        except Exception as exc:  # provider SDK raises several concrete types
            code = _error_code(exc)
            self.stderr.write(f'Key rejected or API unreachable ({code or "error"}): {_error_detail(exc)}')
            self.stderr.write('Get a fresh key at https://aistudio.google.com/apikey')
            return

        usable = [
            _model_name(item) for item in models
            if 'generateContent' in _model_actions(item)
        ]
        self.stdout.write(f'Key OK. {len(usable)} usable model(s) listed.')

        candidates = []
        for name in [model] + PREFERRED_TEXT_MODELS:
            if name in usable and name not in candidates:
                candidates.append(name)
        for name in usable:
            if ('flash' in name and name not in candidates
                    and not any(keyword in name for keyword in SKIP_KEYWORDS)):
                candidates.append(name)

        working = []
        for name in candidates:
            status, detail = self._probe(client, types, name)
            marker = '  <-- configured' if name == model else ''
            if status == 'ok':
                self.stdout.write(self.style.SUCCESS(f'  - {name}: OK{marker}'))
                working.append(name)
            else:
                self.stdout.write(f'  - {name}: {detail}{marker}')

        if model in working:
            self.stdout.write(self.style.SUCCESS(
                'Configured model answers — the concierge AI will work.'
            ))
        elif working:
            self.stdout.write(self.style.WARNING(
                f'Configured model "{model}" does not answer, but these do: '
                + ', '.join(working)
            ))
            self.stdout.write(
                f'Set GEMINI_MODEL={working[0]} in .env, restart the server, done.'
            )
        else:
            self.stderr.write(
                'No text model answered (all overloaded or blocked). '
                'Wait a few minutes and re-run this check.'
            )

    def _probe(self, client, types, model):
        """Send a tiny test prompt; retry once on capacity errors."""
        for attempt in (1, 2):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents='Balas hanya dengan: OK',
                    config=types.GenerateContentConfig(
                        max_output_tokens=10,
                        temperature=0,
                    ),
                )
                text = (getattr(response, 'text', '') or '').strip()
                if text:
                    return ('ok', '')
                return ('fail', 'empty response')
            except Exception as exc:
                code = _error_code(exc)
                if code in (429, 503) and attempt == 1:
                    time.sleep(3)
                    continue
                return ('fail', f'{code or "error"}: {_error_detail(exc)}')
        return ('fail', 'no response')
