"""
高级目标跟踪器

支持多种跟踪方法：
1. 增强模板匹配 + 卡尔曼滤波（默认）
2. YOLO检测 + 外观特征匹配（需要安装ultralytics）
"""

import cv2
import numpy as np
from collections import deque

class KalmanTracker:
    """卡尔曼滤波器用于位置预测"""
    
    def __init__(self, initial_pos):
        """
        初始化卡尔曼滤波器
        状态: [x, y, vx, vy] - 位置和速度
        """
        self.kf = cv2.KalmanFilter(4, 2)  # 4个状态变量，2个测量变量
        
        # 状态转移矩阵 (假设匀速运动)
        self.kf.transitionMatrix = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        
        # 测量矩阵
        self.kf.measurementMatrix = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float32)
        
        # 过程噪声协方差
        self.kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        
        # 测量噪声协方差
        self.kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.5
        
        # 后验误差协方差
        self.kf.errorCovPost = np.eye(4, dtype=np.float32)
        
        # 初始状态
        self.kf.statePost = np.array([
            [initial_pos[0]],
            [initial_pos[1]],
            [0],
            [0]
        ], dtype=np.float32)
    
    def predict(self):
        """预测下一个位置"""
        prediction = self.kf.predict()
        return int(prediction[0, 0]), int(prediction[1, 0])
    
    def update(self, measurement):
        """用测量值更新状态"""
        measurement = np.array([[measurement[0]], [measurement[1]]], dtype=np.float32)
        self.kf.correct(measurement)
        
    def get_velocity(self):
        """获取当前速度"""
        return self.kf.statePost[2, 0], self.kf.statePost[3, 0]


class AppearanceModel:
    """外观模型，用于区分不同目标"""
    
    def __init__(self, frame, bbox, history_size=10):
        self.history_size = history_size
        self.color_hists = deque(maxlen=history_size)
        self.templates = deque(maxlen=history_size)
        
        # 初始化外观特征
        self.update(frame, bbox)
    
    def extract_color_histogram(self, frame, bbox):
        """提取颜色直方图特征"""
        x, y, w, h = map(int, bbox)
        roi = frame[y:y+h, x:x+w]
        
        if roi.size == 0:
            return None
        
        # 转换到HSV空间
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # 计算直方图
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        
        return hist
    
    def update(self, frame, bbox):
        """更新外观模型"""
        x, y, w, h = map(int, bbox)
        
        # 确保bbox在帧范围内
        x = max(0, x)
        y = max(0, y)
        x2 = min(frame.shape[1], x + w)
        y2 = min(frame.shape[0], y + h)
        
        if x2 <= x or y2 <= y:
            return
        
        # 更新颜色直方图
        hist = self.extract_color_histogram(frame, (x, y, x2-x, y2-y))
        if hist is not None:
            self.color_hists.append(hist)
        
        # 更新模板
        template = frame[y:y2, x:x2].copy()
        if template.size > 0:
            self.templates.append(template)
    
    def compare(self, frame, bbox):
        """比较目标与外观模型的相似度"""
        if len(self.color_hists) == 0:
            return 0.5
        
        # 计算当前目标的颜色直方图
        current_hist = self.extract_color_histogram(frame, bbox)
        if current_hist is None:
            return 0.0
        
        # 与历史直方图比较
        similarities = []
        for hist in self.color_hists:
            sim = cv2.compareHist(current_hist, hist, cv2.HISTCMP_CORREL)
            similarities.append(sim)
        
        return np.mean(similarities)


class EnhancedTracker:
    """增强型跟踪器：模板匹配 + 卡尔曼滤波 + 外观模型"""
    
    def __init__(self, frame, bbox, use_deep_learning=False):
        """
        初始化跟踪器
        
        Args:
            frame: 初始帧
            bbox: 初始边界框 (x, y, w, h)
            use_deep_learning: 是否使用深度学习（YOLO）
        """
        self.bbox = tuple(map(int, bbox))
        self.x, self.y, self.w, self.h = self.bbox
        
        # 保存初始尺寸用于参考
        self.initial_w = self.w
        self.initial_h = self.h
        self.aspect_ratio = self.w / self.h  # 保持宽高比
        
        # 尺度自适应参数
        self.current_scale = 1.0
        self.scale_history = deque(maxlen=10)  # 尺度历史用于平滑
        self.scale_history.append(1.0)
        self.min_scale = 0.5   # 最小缩放到50%
        self.max_scale = 1.5   # 最大放大到150%
        self.scale_step = 0.05  # 尺度搜索步长
        self.num_scales = 9     # 搜索的尺度数量
        
        # 中心点
        self.center = (self.x + self.w // 2, self.y + self.h // 2)
        
        # 卡尔曼滤波器
        self.kalman = KalmanTracker(self.center)
        
        # 外观模型
        self.appearance = AppearanceModel(frame, bbox)
        
        # 模板 - 保存原始高分辨率模板
        self.original_template = frame[self.y:self.y+self.h, self.x:self.x+self.w].copy()
        self.template = self.original_template.copy()
        self.template_update_interval = 15
        self.frame_count = 0
        
        # 搜索参数
        self.search_margin = 80  # 基于速度动态调整
        self.min_match_score = 0.4
        
        # 跟踪状态
        self.lost_count = 0
        self.max_lost = 5
        
        # 深度学习检测器
        self.use_deep_learning = use_deep_learning
        self.detector = None
        if use_deep_learning:
            self._init_detector()
    
    def _init_detector(self):
        """初始化YOLO检测器"""
        try:
            from ultralytics import YOLO
            self.detector = YOLO('yolov8n.pt')  # 使用nano模型，速度快
            print("YOLO检测器初始化成功")
        except ImportError:
            print("警告: ultralytics未安装，将使用模板匹配")
            self.use_deep_learning = False
        except Exception as e:
            print(f"YOLO初始化失败: {e}")
            self.use_deep_learning = False
    
    def update(self, frame):
        """
        更新跟踪器
        
        Returns:
            success: 是否成功
            bbox: 新的边界框
            confidence: 置信度
        """
        self.frame_count += 1
        frame_h, frame_w = frame.shape[:2]
        
        # 1. 卡尔曼滤波预测
        predicted_center = self.kalman.predict()
        vx, vy = self.kalman.get_velocity()
        
        # 根据速度动态调整搜索范围
        speed = np.sqrt(vx**2 + vy**2)
        self.search_margin = max(60, min(150, int(self.w + speed * 3)))
        
        # 2. 定义搜索区域（基于预测位置）
        search_x1 = max(0, predicted_center[0] - self.w//2 - self.search_margin)
        search_y1 = max(0, predicted_center[1] - self.h//2 - self.search_margin)
        search_x2 = min(frame_w, predicted_center[0] + self.w//2 + self.search_margin)
        search_y2 = min(frame_h, predicted_center[1] + self.h//2 + self.search_margin)
        
        # 候选位置列表
        candidates = []
        
        # 3. 多尺度模板匹配
        search_region = frame[search_y1:search_y2, search_x1:search_x2]
        
        # 生成要搜索的尺度列表（以当前尺度为中心）
        scales = self._generate_scales()
        
        best_scale_score = -1
        best_scale = self.current_scale
        
        for scale in scales:
            # 根据尺度调整模板大小
            scaled_w = int(self.initial_w * scale)
            scaled_h = int(self.initial_h * scale)
            
            if scaled_w < 10 or scaled_h < 10:
                continue
            
            # 缩放模板
            scaled_template = cv2.resize(self.original_template, (scaled_w, scaled_h))
            
            if search_region.shape[0] <= scaled_h or search_region.shape[1] <= scaled_w:
                continue
            
            result = cv2.matchTemplate(search_region, scaled_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 记录这个尺度的最佳匹配
            if max_val > 0.3:
                abs_x = search_x1 + max_loc[0]
                abs_y = search_y1 + max_loc[1]
                
                # 计算尺度惩罚（偏离当前尺度太多会有惩罚）
                scale_penalty = 1.0 - 0.1 * abs(scale - self.current_scale)
                adjusted_score = max_val * scale_penalty
                
                candidates.append({
                    'bbox': (abs_x, abs_y, scaled_w, scaled_h),
                    'template_score': max_val,
                    'adjusted_score': adjusted_score,
                    'center': (abs_x + scaled_w//2, abs_y + scaled_h//2),
                    'scale': scale
                })
                
                if adjusted_score > best_scale_score:
                    best_scale_score = adjusted_score
                    best_scale = scale
        
        # 4. 如果使用深度学习，添加YOLO检测结果
        if self.use_deep_learning and self.detector:
            candidates.extend(self._detect_with_yolo(frame, search_x1, search_y1, search_x2, search_y2))
        
        # 5. 评估所有候选并选择最佳
        best_candidate = None
        best_score = -1
        
        for cand in candidates:
            # 计算综合得分
            score = self._evaluate_candidate(frame, cand, predicted_center)
            if score > best_score:
                best_score = score
                best_candidate = cand
        
        # 6. 更新或使用预测
        if best_candidate and best_score > self.min_match_score:
            self.lost_count = 0
            
            new_bbox = best_candidate['bbox']
            self.x, self.y, self.w, self.h = map(int, new_bbox)
            
            # 更新尺度（使用平滑）
            if 'scale' in best_candidate:
                new_scale = best_candidate['scale']
                self.scale_history.append(new_scale)
                # 使用中位数平滑，避免突变
                self.current_scale = np.median(list(self.scale_history))
                # 根据平滑后的尺度调整边界框
                new_w = int(self.initial_w * self.current_scale)
                new_h = int(self.initial_h * self.current_scale)
                # 保持中心点不变，调整左上角位置
                old_center_x = self.x + self.w // 2
                old_center_y = self.y + self.h // 2
                self.w = new_w
                self.h = new_h
                self.x = old_center_x - self.w // 2
                self.y = old_center_y - self.h // 2
            
            # 计算中心点（在尺度调整后）
            self.center = (self.x + self.w // 2, self.y + self.h // 2)
            
            # 更新卡尔曼滤波器
            self.kalman.update(self.center)
            
            # 定期更新模板和外观模型
            if self.frame_count % self.template_update_interval == 0 and best_score > 0.6:
                self._update_appearance(frame)
            
            self.bbox = (self.x, self.y, self.w, self.h)
            return True, self.bbox, best_score
        else:
            # 使用预测位置
            self.lost_count += 1
            
            if self.lost_count <= self.max_lost:
                # 使用预测位置
                self.x = predicted_center[0] - self.w // 2
                self.y = predicted_center[1] - self.h // 2
                self.center = predicted_center
                self.bbox = (self.x, self.y, self.w, self.h)
                return True, self.bbox, 0.3  # 低置信度
            else:
                return False, self.bbox, 0.0
    
    def _detect_with_yolo(self, frame, x1, y1, x2, y2):
        """使用YOLO在搜索区域检测车辆"""
        candidates = []
        
        try:
            # 检测整帧（YOLO更擅长全图检测）
            results = self.detector(frame, classes=[2, 5, 7], verbose=False)  # car, bus, truck
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    bx1, by1, bx2, by2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    
                    # 检查是否在搜索区域内
                    cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
                    if x1 <= cx <= x2 and y1 <= cy <= y2:
                        candidates.append({
                            'bbox': (int(bx1), int(by1), int(bx2-bx1), int(by2-by1)),
                            'template_score': conf,
                            'center': (int(cx), int(cy)),
                            'from_yolo': True
                        })
        except Exception as e:
            pass
        
        return candidates
    
    def _generate_scales(self):
        """生成要搜索的尺度列表"""
        # 以当前尺度为中心，生成搜索范围
        center_scale = self.current_scale
        half_range = (self.num_scales // 2) * self.scale_step
        
        scales = []
        for i in range(self.num_scales):
            s = center_scale - half_range + i * self.scale_step
            # 限制在允许范围内
            if self.min_scale <= s <= self.max_scale:
                scales.append(s)
        
        # 确保当前尺度在列表中
        if center_scale not in scales:
            scales.append(center_scale)
        
        return sorted(scales)
    
    def _evaluate_candidate(self, frame, candidate, predicted_center):
        """评估候选目标的综合得分"""
        bbox = candidate['bbox']
        center = candidate['center']
        template_score = candidate.get('template_score', 0.5)
        
        # 1. 模板匹配得分 (0-1)
        score_template = template_score
        
        # 2. 外观相似度得分 (0-1)
        score_appearance = self.appearance.compare(frame, bbox)
        
        # 3. 位置一致性得分 - 与预测位置的距离
        dist = np.sqrt((center[0] - predicted_center[0])**2 + 
                       (center[1] - predicted_center[1])**2)
        max_dist = self.search_margin * 1.5
        score_position = max(0, 1 - dist / max_dist)
        
        # 4. 尺度连续性得分 - 尺度变化应该平滑
        if 'scale' in candidate:
            scale_diff = abs(candidate['scale'] - self.current_scale)
            score_scale = max(0, 1 - scale_diff / 0.3)  # 尺度变化超过30%惩罚较大
        else:
            score_scale = 0.8
        
        # 综合得分（加权平均）
        if candidate.get('from_yolo'):
            # YOLO检测结果给予更高权重
            total_score = (score_template * 0.35 + 
                          score_appearance * 0.25 + 
                          score_position * 0.25 + 
                          score_scale * 0.15)
        else:
            total_score = (score_template * 0.3 + 
                          score_appearance * 0.3 + 
                          score_position * 0.25 + 
                          score_scale * 0.15)
        
        return total_score
    
    def _update_appearance(self, frame):
        """更新外观模型和模板"""
        x, y, w, h = self.x, self.y, self.w, self.h
        
        # 确保在帧范围内
        x = max(0, x)
        y = max(0, y)
        x2 = min(frame.shape[1], x + w)
        y2 = min(frame.shape[0], y + h)
        
        if x2 > x and y2 > y:
            current_roi = frame[y:y2, x:x2].copy()
            self.template = current_roi
            
            # 更新原始模板（缩放到初始尺寸以保持一致性）
            if self.initial_w > 0 and self.initial_h > 0:
                self.original_template = cv2.resize(current_roi, (self.initial_w, self.initial_h))
            
            self.appearance.update(frame, (x, y, x2-x, y2-y))


def check_yolo_available():
    """检查YOLO是否可用"""
    try:
        from ultralytics import YOLO
        return True
    except ImportError:
        return False


def get_tracker_info():
    """获取可用跟踪器信息"""
    info = {
        'enhanced': True,
        'yolo': check_yolo_available()
    }
    return info
