import { useState } from 'react';
import { X, ThumbsUp, Meh, ThumbsDown, Star } from 'lucide-react';

interface FeedbackDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (rating: 'helpful' | 'neutral' | 'not-helpful') => void;
}

export function FeedbackDialog({ isOpen, onClose, onSubmit }: FeedbackDialogProps) {
  const [selectedRating, setSelectedRating] = useState<'helpful' | 'neutral' | 'not-helpful' | null>(null);

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (selectedRating) {
      onSubmit(selectedRating);
      onClose();
    }
  };

  const handleSkip = () => {
    onClose();
    // 跳过后跳转到首页
    window.location.href = '/';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div 
        className="absolute inset-0 bg-black/50" 
        onClick={onClose}
      />
      
      {/* 弹框内容 */}
      <div className="relative bg-background rounded-lg border p-6 shadow-lg w-full max-w-[calc(100%-2rem)] sm:max-w-md">
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-sm opacity-70 hover:opacity-100 transition-opacity"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>

        {/* 标题 */}
        <div className="flex items-center space-x-2 mb-2">
          <Star className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold leading-none">评价这份报告</h2>
        </div>

        {/* 描述 */}
        <p className="text-sm text-muted-foreground mb-6">
          您的反馈将帮助我们改进分析质量，请选择您对这份市场洞察报告的评价
        </p>

        {/* 选项 */}
        <div className="space-y-3 mb-6">
          {/* 有价值 */}
          <button
            onClick={() => setSelectedRating('helpful')}
            className={`w-full flex items-start gap-4 rounded-xl py-6 px-6 border-2 transition-all duration-200 cursor-pointer ${
              selectedRating === 'helpful'
                ? 'bg-green-100 border-green-300'
                : 'bg-green-50 hover:bg-green-100 border-green-200'
            }`}
          >
            <ThumbsUp className="h-6 w-6 text-green-600 shrink-0 mt-0.5" />
            <div className="text-left">
              <h4 className="font-medium text-foreground mb-1">有价值</h4>
              <p className="text-sm text-muted-foreground">这份报告对我很有帮助</p>
            </div>
          </button>

          {/* 一般 */}
          <button
            onClick={() => setSelectedRating('neutral')}
            className={`w-full flex items-start gap-4 rounded-xl py-6 px-6 border-2 transition-all duration-200 cursor-pointer ${
              selectedRating === 'neutral'
                ? 'bg-yellow-100 border-yellow-300'
                : 'bg-yellow-50 hover:bg-yellow-100 border-yellow-200'
            }`}
          >
            <Meh className="h-6 w-6 text-yellow-600 shrink-0 mt-0.5" />
            <div className="text-left">
              <h4 className="font-medium text-foreground mb-1">一般</h4>
              <p className="text-sm text-muted-foreground">报告还可以，但有改进空间</p>
            </div>
          </button>

          {/* 无价值 */}
          <button
            onClick={() => setSelectedRating('not-helpful')}
            className={`w-full flex items-start gap-4 rounded-xl py-6 px-6 border-2 transition-all duration-200 cursor-pointer ${
              selectedRating === 'not-helpful'
                ? 'bg-red-100 border-red-300'
                : 'bg-red-50 hover:bg-red-100 border-red-200'
            }`}
          >
            <ThumbsDown className="h-6 w-6 text-red-600 shrink-0 mt-0.5" />
            <div className="text-left">
              <h4 className="font-medium text-foreground mb-1">无价值</h4>
              <p className="text-sm text-muted-foreground">这份报告对我没有帮助</p>
            </div>
          </button>
        </div>

        {/* 底部按钮 */}
        <div className="flex justify-end gap-3">
          <button
            onClick={handleSkip}
            className="inline-flex items-center justify-center rounded-md border bg-background px-4 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors shadow-xs"
          >
            跳过
          </button>
          <button
            onClick={handleSubmit}
            disabled={!selectedRating}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:pointer-events-none transition-colors shadow-xs"
          >
            提交评价
          </button>
        </div>
      </div>
    </div>
  );
}

