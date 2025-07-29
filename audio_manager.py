"""
오디오 효과음 관리 모듈
다른 모듈에서 재사용 가능한 오디오 시스템
"""

import os
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
import logging
from pathlib import Path


class AudioManager:
    """오디오 효과음 관리 클래스"""
    
    def __init__(self, sounds_dir="src/sounds"):
        self.sounds_dir = sounds_dir
        self.audio_cache = {}
        self._initialized = False
        
        # 기본 오디오 파일 매핑
        self.default_sounds = {
            'AP_Engage': 'AP_Engage.mp3',
            'AP_Disengage': 'AP_Disengage.mp3', 
            'NoA_Engage': 'NoA_Engage.mp3',
            'rec_start_voice': 'rec_start_voice.mp3',
            'rec_stop_voice': 'rec_stop_voice.mp3',
            'chime_single': 'chime_single.mp3',
            'chime_hi_lo': 'chime_hi_lo.mp3'
        }
        
        self.initialize()
    
    def initialize(self):
        """오디오 시스템 초기화"""
        if self._initialized:
            return
            
        try:
            # 최적 지연시간 설정 (성능 vs 안정성 균형)
            sd.default.latency = 'low' 
            # CPU 집약적 환경을 위한 큰 버퍼 (끊김 방지 우선)
            sd.default.blocksize = 2048
            # 오디오 스트림 설정 최적화
            sd.default.dtype = 'float32'  # 일관된 데이터 타입
            # 더 관대한 지연시간 설정으로 안정성 향상
            sd.default.latency = ['low', 'high']  # 낮은 지연 시도, 실패시 높은 지연
            
            # 오디오 파일 프리로드
            self._preload_audio_files()
            
            # sounddevice 스트림 미리 워밍업 (지연시간 개선)
            self._warmup_audio_stream()
            
            self._initialized = True
            print("오디오 시스템 초기화 완료")
            
        except Exception as e:
            logging.error(f"오디오 시스템 초기화 중 오류: {e}")
            print(f"오디오 시스템 초기화 중 오류: {e}")
    
    def _warmup_audio_stream(self):
        """오디오 스트림 워밍업 - 첫 재생 지연 제거"""
        try:
            # 매우 짧은 무음 재생으로 스트림 초기화
            silence = np.zeros((100,), dtype=np.float32)  # 100샘플 무음
            sd.play(silence, 22050, blocksize=2048)
            sd.wait()  # 완료 대기
            print("오디오 스트림 워밍업 완료")
        except Exception as e:
            logging.warning(f"오디오 스트림 워밍업 실패: {e}")
    
    def _get_resource_path(self, relative_path):
        """리소스 파일 경로 반환 (PyInstaller 호환)"""
        try:
            # PyInstaller로 빌드된 경우
            import sys
            base_path = sys._MEIPASS
        except Exception:
            # 개발 환경
            base_path = os.path.abspath(".")
        
        return os.path.join(base_path, relative_path)
    
    def _preload_audio_files(self):
        """오디오 파일을 미리 메모리에 로드"""
        try:
            # 기본 사운드 파일들 로드
            for sound_key, filename in self.default_sounds.items():
                file_path = os.path.join(self.sounds_dir, filename)
                resolved_path = self._get_resource_path(file_path)
                
                if os.path.exists(resolved_path):
                    data, fs = sf.read(resolved_path)
                    # 모노 채널인 경우 스테레오로 변환
                    if len(data.shape) == 1:
                        data = np.column_stack((data, data))
                    
                    self.audio_cache[sound_key] = {
                        'data': data,
                        'fs': fs
                    }
                else:
                    logging.warning(f"오디오 파일을 찾을 수 없습니다: {resolved_path}")
            
            print(f"오디오 파일 {len(self.audio_cache)}개 로드 완료")
            
        except Exception as e:
            logging.error(f"오디오 파일 로드 중 오류: {e}")
            print(f"오디오 파일 로드 중 오류: {e}")
    
    def add_sound(self, sound_key, file_path):
        """새로운 사운드 파일 추가"""
        try:
            resolved_path = self._get_resource_path(file_path)
            if not os.path.exists(resolved_path):
                logging.error(f"오디오 파일을 찾을 수 없습니다: {resolved_path}")
                return False
                
            data, fs = sf.read(resolved_path)
            
            # 모노 채널인 경우 스테레오로 변환
            if len(data.shape) == 1:
                data = np.column_stack((data, data))
            
            self.audio_cache[sound_key] = {
                'data': data,
                'fs': fs
            }
            
            logging.info(f"사운드 추가됨: {sound_key}")
            return True
            
        except Exception as e:
            logging.error(f"사운드 추가 중 오류 ({sound_key}): {e}")
            return False
    
    def play_sound(self, sound_key):
        """사운드 재생 (지연 없는 비동기)"""
        if sound_key not in self.audio_cache:
            logging.warning(f"사운드 키를 찾을 수 없습니다: {sound_key}")
            return False
        
        def _play_thread():
            try:
                # Windows 스레드 우선순위 설정 (CPU 집약적 작업 중 안정적 재생)
                try:
                    import ctypes
                    ctypes.windll.kernel32.SetThreadPriority(
                        ctypes.windll.kernel32.GetCurrentThread(), 2  # THREAD_PRIORITY_ABOVE_NORMAL
                    )
                except Exception as e:
                    logging.debug(f"Windows 스레드 우선순위 설정 실패 (무시됨): {e}")
                
                audio = self.audio_cache[sound_key]
                # 더 큰 버퍼로 끊김 방지 (CPU 집약적 환경 대응)
                sd.play(audio['data'], audio['fs'], blocksize=2048)
                
            except Exception as e:
                logging.error(f"오디오 재생 중 오류 ({sound_key}): {e}")
        
        # 고우선순위 스레드로 생성
        thread = threading.Thread(
            target=_play_thread, 
            daemon=True, 
            name=f"AudioPlay_{sound_key}"
        )
        thread.start()
        return True
    
    def get_audio_data(self, sound_key):
        """음성 합성용 오디오 데이터 반환"""
        if sound_key in self.audio_cache:
            return self.audio_cache[sound_key]
        else:
            logging.warning(f"사운드 키를 찾을 수 없습니다: {sound_key}")
            return None
    
    def get_available_sounds(self):
        """사용 가능한 사운드 목록 반환"""
        return list(self.audio_cache.keys())
    
    def stop_all_sounds(self):
        """모든 사운드 재생 중지"""
        try:
            sd.stop()
        except Exception as e:
            logging.error(f"사운드 중지 중 오류: {e}")


# 전역 인스턴스 (eager initialization으로 성능 최적화)
_audio_manager_instance = AudioManager()

def get_audio_manager():
    """오디오 매니저 싱글톤 인스턴스 반환"""
    return _audio_manager_instance

def play_sound(sound_key):
    """사운드 재생 (편의 함수)"""
    return get_audio_manager().play_sound(sound_key)

def get_audio_data(sound_key):
    """음성 합성용 오디오 데이터 반환 (편의 함수)"""
    return get_audio_manager().get_audio_data(sound_key)