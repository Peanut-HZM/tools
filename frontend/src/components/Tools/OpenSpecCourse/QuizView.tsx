/**
 * 测验界面组件
 */
import React, { useState } from 'react';
import { Chapter, Quiz } from '../../../services/openspecCourse';
import { submitQuiz } from '../../../services/openspecCourse';

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
      <div className="bg-white/5 backdrop-blur-sm rounded-xl p-8 border border-white/10">
        <div className="text-center text-white">正在加载测验...</div>
      </div>
    );
  }

  if (error && !quiz) {
    return (
      <div className="bg-red-500/20 border border-red-500 rounded-xl p-6 text-red-300">
        {error}
      </div>
    );
  }

  if (!quiz) {
    return (
      <div className="bg-white/5 backdrop-blur-sm rounded-xl p-8 border border-white/10">
        <div className="text-center text-white">暂无测验</div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white mb-2">📝 {quiz.title}</h2>
        <p className="text-white/60">
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
              className={`bg-white/5 backdrop-blur-sm rounded-xl p-6 border ${
                isCorrect
                  ? 'border-green-500 bg-green-500/10'
                  : isWrong
                  ? 'border-red-500 bg-red-500/10'
                  : 'border-white/10'
              }`}
            >
              <div className="flex items-start space-x-3 mb-4">
                <span className="text-lg font-semibold text-white">
                  {qIndex + 1}.
                </span>
                <div className="flex-1">
                  <p className="text-white mb-4">{question.question_text}</p>

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
                          className={`w-full text-left p-4 rounded-lg transition-all ${
                            showCorrect
                              ? 'bg-green-500 border-green-500 text-white'
                              : showWrong
                              ? 'bg-red-500 border-red-500 text-white'
                              : isSelected
                              ? 'bg-yellow-500/20 border-yellow-500 text-white'
                              : 'bg-gray-800/50 border border-gray-700 text-white hover:bg-gray-700/50'
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
                      isCorrect ? 'bg-green-500/20' : 'bg-blue-500/20'
                    }`}>
                      <p className="text-white/80">
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
              ? 'bg-green-500/20 border-green-500'
              : 'bg-red-500/20 border-red-500'
          }`}
        >
          <div className="text-center">
            <div className="text-4xl mb-2">{result.passed ? '🎉' : '😢'}</div>
            <div className="text-2xl font-bold text-white mb-2">
              {result.passed ? '恭喜通过！' : '未能通过'}
            </div>
            <div className="text-white/60">
              得分：{result.score.toFixed(1)}% ({result.correct_count}/{result.total_questions})
            </div>
            {!result.passed && (
              <button
                onClick={() => {
                  setSubmitted(false);
                  setAnswers({});
                  setResult(null);
                }}
                className="mt-4 px-6 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
              >
                重试
              </button>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      {!submitted && (
        <div className="mt-8 flex items-center justify-between">
          <button
            onClick={onCancel}
            className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={Object.keys(answers).length < quiz.questions.length}
            className="px-6 py-3 bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-black rounded-xl transition-colors font-medium"
          >
            提交答案
          </button>
        </div>
      )}
    </div>
  );
};

export default QuizView;
