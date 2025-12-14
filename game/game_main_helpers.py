"""
Вспомогательные функции для main() в PyGameBall.py.
Содержит подфункции для обработки событий, обновления игры и отрисовки.
"""

import time
import random
from typing import Tuple, Optional, Dict, Any
import pygame

try:
    from .game_config import (
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        BRICK_ROWS,
        BRICK_COLS,
        MAX_LIVES,
        FPS,
        SEPARATION_ZONE_TOP,
        SEPARATION_ZONE_BOTTOM,
        PADDLE_WIDTH,
        PADDLE_SPEED,
        BALL_SIZE,
    )
    from .game_models import Paddle, Ball
    from .game_utils import build_bricks, create_ai_player
    from .game_rendering import draw_bricks, draw_hud, draw_start_hint
    from ai.ai_player import AIPlayer
except ImportError:
    from game.game_config import (
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        BRICK_ROWS,
        BRICK_COLS,
        MAX_LIVES,
        FPS,
        SEPARATION_ZONE_TOP,
        SEPARATION_ZONE_BOTTOM,
        PADDLE_WIDTH,
        PADDLE_SPEED,
        BALL_SIZE,
    )
    from game.game_models import Paddle, Ball
    from game.game_utils import build_bricks, create_ai_player
    from game.game_rendering import draw_bricks, draw_hud, draw_start_hint
    from ai.ai_player import AIPlayer


def handle_game_events(
    events: list,
    sound_enabled: bool,
    ball: Ball,
    settings_manager: Any,
    training_mode: bool,
    key_1_press_count: int,
    key_1_last_press_time: float,
    KEY_1_RESET_TIME: float,
    bricks: list,
    game_over: bool,
    lives_left: int,
    game_start_time: float,
    score: int,
    player_name: str,
    highscore_manager: Any,
    screen: pygame.Surface,
    font: pygame.font.Font,
    big_font: pygame.font.Font,
) -> Tuple[bool, bool, int, float, list, bool]:
    """
    Обрабатывает события игры.
    
    Returns:
        Tuple: (running, sound_enabled, key_1_press_count, key_1_last_press_time, bricks, game_over)
    """
    running = True
    
    for event in events:
        if event.type == pygame.QUIT:
            running = False
            break
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
                break
            elif event.key == pygame.K_m:
                if sound_enabled:
                    pygame.mixer.music.stop()
                    sound_enabled = False
                else:
                    pygame.mixer.music.play(-1)
                    sound_enabled = True
            elif event.key == pygame.K_UP:
                ball.increase_speed(settings_manager)
            elif event.key == pygame.K_DOWN:
                ball.decrease_speed(settings_manager)
            elif event.key == pygame.K_1 or event.key == ord('1'):
                current_time = time.time()
                if current_time - key_1_last_press_time > KEY_1_RESET_TIME:
                    key_1_press_count = 0
                
                key_1_press_count += 1
                key_1_last_press_time = current_time
                
                if key_1_press_count >= 3:
                    bricks = []
                    key_1_press_count = 0
                    if not training_mode and lives_left > 0:
                        from .game_ui import trigger_instant_victory
                        game_time_seconds = int(time.time() - game_start_time)
                        try:
                            sound_enabled, restart_game, exit_game = trigger_instant_victory(
                                screen,
                                font,
                                big_font,
                                score,
                                player_name,
                                game_time_seconds,
                                highscore_manager,
                                settings_manager,
                                ball,
                            )
                            if exit_game:
                                pygame.quit()
                                return False, sound_enabled, key_1_press_count, key_1_last_press_time, bricks, True
                        except Exception as e:
                            pass
    
    return running, sound_enabled, key_1_press_count, key_1_last_press_time, bricks, game_over


def update_game_state(
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    game_start_time: float,
    frame_counter: int,
    logger: Any,
) -> None:
    """Обновляет состояние игры для AI системы."""
    if training_mode and ai_player is not None:
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] Вызываем update_game_state...")
        ai_player.update_game_state(
            ball, paddle, bricks, score, int(game_start_time)
        )
        if frame_counter <= 3:
            logger.debug(f"[AI DEBUG] update_game_state завершен")


def update_ball_physics(
    game_started: bool,
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
    frame_counter: int,
    logger: Any,
) -> Tuple[list, int]:
    """
    Обновляет физику мяча и обрабатывает столкновения.
    
    Returns:
        Tuple: (bricks, score)
    """
    if game_started:
        ball_was_at_top = ball.rect.top <= 0 and ball.vel_y < 0
        
        try:
            ball.update()
        except Exception as e:
            if not getattr(__import__('sys'), 'frozen', False):
                print(f"[ERROR] Ошибка в ball.update(): {e}")
            raise
        
        just_bounced = getattr(ball, '_just_bounced', False)
        bounce_frame = getattr(ball, '_bounce_frame', -1)
        if (ball.rect.colliderect(paddle.rect) and ball.vel_y > 0 
            and not (just_bounced and (bounce_frame == frame_counter or bounce_frame == frame_counter - 1))):
            ball_radius = BALL_SIZE // 2
            min_distance = abs(ball.vel_y) + 15
            ball.rect.centery = paddle.rect.top - ball_radius - min_distance
            if ball.vel_y >= 0:
                ball.vel_y = -ball.get_speed()
            ball._just_bounced = True
            ball._bounce_frame = frame_counter
        
        if just_bounced and frame_counter - bounce_frame > 3:
            ball._just_bounced = False
        
        if game_started and ball.vel_y == 0:
            ball.vel_y = -ball.get_speed()
            if training_mode and ai_player is not None:
                ai_player.performance_logger.log_ball_paddle_positions(
                    ball.rect.centerx,
                    ball.rect.centery,
                    ball.vel_x,
                    ball.vel_y,
                    paddle.rect.x,
                    paddle.rect.y,
                    paddle.rect.width,
                    paddle.rect.height,
                    "VEL_Y_ZERO_FIXED"
                )
        
        should_log = False
        if training_mode:
            if frame_counter % 10 == 0:
                should_log = True
            elif ball.rect.colliderect(paddle.rect) and abs(ball.vel_y) < 0.1:
                should_log = True
        
        if should_log and ai_player is not None:
            try:
                ai_player.performance_logger.log_ball_paddle_positions(
                    ball.rect.centerx,
                    ball.rect.centery,
                    ball.vel_x,
                    ball.vel_y,
                    paddle.rect.x,
                    paddle.rect.y,
                    paddle.rect.width,
                    paddle.rect.height,
                    "frame_update"
                )
            except Exception:
                pass
        
        if ball_was_at_top and ball.vel_y > 0:
            if training_mode and ai_player is not None:
                ai_player.empty_bounce_tracker["ceiling_bounces"] += 1
        
        ball_hits_paddle_top = False
        ball_hits_paddle_side = False
        
        just_bounced = getattr(ball, '_just_bounced', False)
        bounce_frame = getattr(ball, '_bounce_frame', -1)
        if just_bounced and (bounce_frame == frame_counter or bounce_frame == frame_counter - 1):
            ball_hits_paddle_top = False
        else:
            ball_hits_paddle_top = (
                ball.rect.colliderect(paddle.rect) 
                and ball.vel_y > 0
                and paddle.rect.left - 5 <= ball.rect.centerx <= paddle.rect.right + 5
                and ball.rect.bottom >= paddle.rect.top
                and ball.rect.bottom <= paddle.rect.top + 15
                and ball.rect.top < paddle.rect.top + 10
            )
        
        ball_hits_paddle_side = (
            ball.rect.colliderect(paddle.rect)
            and ball.vel_y > 0
            and not ball_hits_paddle_top
            and (
                (ball.rect.right >= paddle.rect.left and ball.rect.right <= paddle.rect.left + 10 and ball.rect.centerx < paddle.rect.left)
                or
                (ball.rect.left <= paddle.rect.right and ball.rect.left >= paddle.rect.right - 10 and ball.rect.centerx > paddle.rect.right)
                or
                (ball.rect.bottom < paddle.rect.top and (ball.rect.centerx < paddle.rect.left or ball.rect.centerx > paddle.rect.right))
            )
        )
        
        if ball_hits_paddle_side:
            if training_mode and ai_player is not None:
                ai_result = {
                    "action_type": "paddle_side_hit",
                    "success": False,
                    "confidence": 0.0,
                    "ball_speed": ball.get_speed(),
                    "remaining_bricks": len(bricks),
                }
                ai_player.learn_from_result(ai_result)
            return bricks, score
        
        ball_stuck = (
            ball.rect.colliderect(paddle.rect)
            and ball.vel_y == 0
            and not ball_hits_paddle_top
            and game_started
        )
        
        if ball_stuck:
            if training_mode and ai_player is not None:
                ai_player.performance_logger.log_ball_paddle_positions(
                    ball.rect.centerx,
                    ball.rect.centery,
                    ball.vel_x,
                    ball.vel_y,
                    paddle.rect.x,
                    paddle.rect.y,
                    paddle.rect.width,
                    paddle.rect.height,
                    "BALL_STUCK_DETECTED"
                )
            
            ball_radius = BALL_SIZE // 2
            ball.rect.centery = paddle.rect.top - ball_radius - 15
            if ball.rect.colliderect(paddle.rect):
                ball.rect.centery = paddle.rect.top - ball_radius - 25
            if ball.vel_y <= 0:
                ball.vel_y = -ball.get_speed()
            if abs(ball.vel_x) < 2:
                ball.vel_x = random.choice([-ball.get_speed(), ball.get_speed()])
            
            if training_mode and ai_player is not None:
                ai_player.performance_logger.log_ball_paddle_positions(
                    ball.rect.centerx,
                    ball.rect.centery,
                    ball.vel_x,
                    ball.vel_y,
                    paddle.rect.x,
                    paddle.rect.y,
                    paddle.rect.width,
                    paddle.rect.height,
                    "BALL_STUCK_FIXED"
                )
            return bricks, score
        
        if ball_hits_paddle_top:
            if training_mode and ai_player is not None:
                ai_player.performance_logger.log_ball_paddle_positions(
                    ball.rect.centerx,
                    ball.rect.centery,
                    ball.vel_x,
                    ball.vel_y,
                    paddle.rect.x,
                    paddle.rect.y,
                    paddle.rect.width,
                    paddle.rect.height,
                    "PADDLE_TOP_HIT"
                )
            
            paddle_center = paddle.rect.centerx
            ball_center = ball.rect.centerx
            offset = (ball_center - paddle_center) / (paddle.rect.width / 2)
            offset = max(-1.0, min(1.0, offset))
            
            ball.bounce_vertical()
            if ball.vel_y >= 0:
                ball.vel_y = -ball.get_speed()
            ball.vel_x = int(offset * ball.get_speed())
            
            ball_radius = BALL_SIZE // 2
            min_distance = abs(ball.vel_y) + 10
            ball.rect.centery = paddle.rect.top - ball_radius - min_distance
            
            if ball.rect.colliderect(paddle.rect):
                ball.rect.centery = paddle.rect.top - ball_radius - (min_distance + 10)
            
            if ball.rect.bottom >= paddle.rect.top:
                ball.rect.centery = paddle.rect.top - ball_radius - (min_distance + 5)
            
            ball._just_bounced = True
            if not hasattr(ball, '_bounce_frame'):
                ball._bounce_frame = 0
            ball._bounce_frame = frame_counter
            
            min_horizontal_speed = max(2, ball.get_speed() // 2)
            if abs(ball.vel_x) < min_horizontal_speed:
                if ball.rect.centerx < SCREEN_WIDTH // 2:
                    ball.vel_x = min_horizontal_speed
                else:
                    ball.vel_x = -min_horizontal_speed
                ball.vel_x += random.choice([-1, 0, 1])
            
            if hasattr(ball, '_last_vel_x') and abs(ball._last_vel_x) <= 1 and abs(ball.vel_x) <= 1:
                ball.vel_x = random.choice([-min_horizontal_speed, min_horizontal_speed])
            
            ball._last_vel_x = ball.vel_x
            max_horizontal = ball.get_speed()
            ball.vel_x = max(-max_horizontal, min(max_horizontal, ball.vel_x))
            
            for attempt in range(5):
                if ball.rect.colliderect(paddle.rect) or ball.rect.bottom >= paddle.rect.top:
                    ball.rect.centery = paddle.rect.top - ball_radius - (25 + attempt * 5)
                else:
                    break
            
            if ball.vel_y == 0:
                ball.vel_y = -ball.get_speed()
            elif ball.vel_y >= 0:
                ball.vel_y = -ball.get_speed()
            if abs(ball.vel_y) < ball.get_speed():
                ball.vel_y = -ball.get_speed()
            
            if training_mode and ai_player is not None:
                ai_result = {
                    "action_type": "paddle_bounce",
                    "success": True,
                    "confidence": 0.8,
                    "movement_distance": abs(offset * paddle.rect.width),
                    "ball_speed": ball.get_speed(),
                    "remaining_bricks": len(bricks),
                }
                ai_player.learn_from_result(ai_result)
                ai_player._reevaluate_after_bounce()
        
        hit_index = -1
        if bricks and ball.rect.bottom <= SEPARATION_ZONE_TOP + 50:
            try:
                hit_index = ball.rect.collidelist(bricks)
            except Exception:
                hit_index = -1
        
        if hit_index != -1:
            ball.bounce_vertical()
            destroyed_brick = bricks.pop(hit_index)
            score += 1
            
            if training_mode and ai_player is not None:
                ai_player.empty_bounce_tracker["consecutive_empty_bounces"] = 0
                ai_player.empty_bounce_tracker["ceiling_bounces"] = 0
                
                try:
                    ai_result = {
                        "action_type": "brick_hit",
                        "success": True,
                        "confidence": 1.0,
                        "bricks_destroyed": [
                            {"x": destroyed_brick.x, "y": destroyed_brick.y}
                        ],
                        "remaining_bricks": len(bricks),
                        "ball_speed": ball.get_speed(),
                    }
                    ai_player.learn_from_result(ai_result)
                except Exception:
                    pass
    
    return bricks, score


def render_game_frame(
    screen: pygame.Surface,
    font: pygame.font.Font,
    ball: Ball,
    paddle: Paddle,
    bricks: list,
    score: int,
    lives_left: int,
    game_started: bool,
    training_mode: bool,
    ai_player: Optional[AIPlayer],
) -> None:
    """Отрисовывает один кадр игры."""
    screen.fill((0, 0, 0))
    
    if bricks:
        draw_bricks(screen, bricks)
    
    ball.draw(screen)
    paddle.draw(screen)
    
    draw_hud(
        screen,
        score,
        lives_left,
        font,
        ball,
        training_mode,
        ai_player,
    )
    
    if not game_started:
        draw_start_hint(screen, font)
    
    pygame.display.flip()
