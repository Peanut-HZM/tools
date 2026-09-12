/**
 * 测验界面组件
 */
import React, { useState } from 'react';
import { Chapter, Quiz } from '../../../services/openspecCourse';
import { submitQuiz } from '../../../services/openspecCourse';
import { Button } from '@/components/ui/Button';

interface QuizViewProps {
  chapter: Chapter;
  onComplete: (passed: boolean, chapterId: number) => void;
  onCancel: () => void;
}

const QuizView: React.FC<QuizViewProps> = ({ chapter, onComplete, onCancel }) => {
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<number, number[]>>({});
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<any>(null);

  // Load quiz on mount
  React.useEffect(() => {
    const loadQuiz = async () => {
      try {
        setLoading(true);
        // 这里需要从 API 获取测验数据
        // 为了简化，我们假设 quiz 已经包含在 chapter 中
        if (chapter.quiz) {
          setQuiz(chapter.quiz);
        }
      } catch (err) {
        setError('加载测验失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadQuiz();
  }, [chapter]);

  const handleOptionSelect = (questionId: number, optionIndex: number, isMultiple: boolean) => {
    if (submitted) return;

    setAnswers((prev) => {
      const currentAnswers = prev[questionId] || [];

      if (isMultiple) {
        // 多选题：切换选项
        if (currentAnswers.includes(optionIndex)) {
          return {
            ...prev,
            [questionId]: currentAnswers.filter((i) => i !== optionIndex),
          };
        } else {
          return {
            ...prev,
            [questionId]: [...currentAnswers, optionIndex],
          };
        }
      } else {
        // 单选题：只保留一个选项
        return {
          ...prev,
          [questionId]: [optionIndex],
        };
      }
    });
  };

  const handleSubmit = async () => {
    if (!quiz) return;

    try {
      setLoading(true);
      const quizResult = await submitQuiz(quiz.id, answers);
      setResult(quizResult);
      setSubmitted(true);

      if (quizResult.passed) {
        onComplete(true, chapter.id);
      }
    } catch (err) {
      setError('提交测验失败，请重试');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !quiz) {
    return (
      <div className="glass-card rounded-xl p-8">
        <div className="text-center text-ink-muted">正在加载测验...</div>
      </div>
    );
  }

  if (error && !quiz) {
    return (
      // 错误提示走语义 danger token（与其他工具页错误条同款规格）
      <div className="bg-danger/10 border border-danger rounded-xl p-6 text-danger">
        {error}
      </div>
    );
  }

  if (!quiz) {
    return (
      <div className="glass-card rounded-xl p-8">
        <div className="text-center text-ink-muted">暂无测验</div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-ink mb-2">📝 {quiz.title}</h2>
        <p className="text-ink-muted">
          共 {quiz.questions.length} 题，及格分数：{quiz.passing_score}%
        </p>
      </div>

      {/* Questions */}
      <div className="space-y-6">
        {quiz.questions.map((question, qIndex) => {
          const isMultiple = question.question_type === 'multiple';
          const userAnswer = answers[question.id] || [];
          const isCorrect =
            submitted &&
            JSON.stringify(userAnswer.sort()) ===
              JSON.stringify(question.correct_answer.split(',').map(Number).sort());
          const isWrong =
            submitted &&
            !isCorrect;

          return (
            <div
              key={question.id}
              // 题卡：默认玻璃卡片；判分后按对错叠加语义色底（glass-card 自带描边，仅在判分态覆盖边色）
              className={`rounded-xl p-6 border ${
                isCorrect
                  ? 'bg-accent-success/10 border-accent-success'
                  : isWrong
                  ? 'bg-danger/10 border-danger'
                  : 'glass-card'
              }`}
            >
              <div className="flex items-start space-x-3 mb-4">
                <span className="text-lg font-semibold text-ink">
                  {qIndex + 1}.
                </span>
                <div className="flex-1">
                  <p className="text-ink mb-4">{question.question_text}</p>

                  {/* Options */}
                  <div className="space-y-2">
                    {question.options.map((option) => {
                      const isSelected = userAnswer.includes(option.option_index);
                      const showCorrect =
                        submitted &&
                        question.correct_answer.split(',').map(Number).includes(option.option_index);
                      const showWrong =
                        submitted &&
                        isSelected &&
                        !question.correct_answer.split(',').map(Number).includes(option.option_index);

                      return (
                        <button
                          key={option.id}
                          onClick={() =>
                            handleOptionSelect(question.id, option.option_index, isMultiple)
                          }
                          disabled={submitted}
                          className={`w-full text-left p-4 rounded-lg transition-all border ${
                            showCorrect
                              ? 'bg-accent-success/20 border-accent-success text-ink'
                              : showWrong
                              ? 'bg-danger/20 border-danger text-ink'
                              : isSelected
                              ? 'bg-accent-warning/20 border-accent-warning text-ink'
                              : 'bg-surface-2/40 border-border text-ink hover:bg-surface-2/60'
                          }`}
                        >
                          <span className="font-medium mr-2">
                            {String.fromCharCode(65 + option.option_index)}.
                          </span>
                          {option.option_text}
                        </button>
                      );
                    })}
                  </div>

                  {/* Explanation */}
                  {submitted && question.explanation && (
                    <div className={`mt-4 p-4 rounded-lg ${
                      isCorrect ? 'bg-accent-success/10' : 'bg-accent-info/10'
                    }`}>
                      <p className="text-ink-muted">
                        <span className="font-semibold">💡 解析：</span>
                        {question.explanation}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Result */}
      {submitted && result && (
        <div
          className={`mt-8 p-6 rounded-xl border ${
            result.passed
              ? 'bg-accent-success/15 border-accent-success'
              : 'bg-danger/15 border-danger'
          }`}
        >
          <div className="text-center">
            <div className="text-4xl mb-2">{result.passed ? '🎉' : '😢'}</div>
            <div className="text-2xl font-bold text-ink mb-2">
              {result.passed ? '恭喜通过！' : '未能通过'}
            </div>
            <div className="text-ink-muted">
              得分：{result.score.toFixed(1)}% ({result.correct_count}/{result.total_questions})
            </div>
            {!result.passed && (
              <Button
                variant="destructive"
                onClick={() => {
                  setSubmitted(false);
                  setAnswers({});
                  setResult(null);
                }}
                className="mt-4"
              >
                重试
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      {!submitted && (
        <div className="mt-8 flex items-center justify-between">
          <Button
            variant="secondary"
            onClick={onCancel}
          >
            取消
          </Button>
          {/* 提交为测验主操作：走 default 变体（品牌渐变），禁用态由 Button 基类统一处理 */}
          <Button
            onClick={handleSubmit}
            disabled={Object.keys(answers).length < quiz.questions.length}
          >
            提交答案
          </Button>
        </div>
      )}
    </div>
  );
};

export default QuizView;
