/**
 * 测验表单组件（包含题目和选项的嵌套编辑）
 */
import React, { useState, useEffect } from 'react';
import { useQuizStore } from '../../../stores/courseAdminStore';
import type { QuizCreate, QuizUpdate, QuizQuestion, QuizOption } from '../../../services/openspecCourseAdmin';

interface QuizFormProps {
  chapterId: number;
  quizId: number | null;
  onClose: () => void;
}

interface QuestionFormData {
  id?: number;
  question_text: string;
  question_type: 'single' | 'multiple' | 'true_false';
  correct_answer: string;
  explanation: string;
  order: number;
  options: OptionFormData[];
}

interface OptionFormData {
  id?: number;
  option_text: string;
  option_index: number;
}

const QuizForm: React.FC<QuizFormProps> = ({ chapterId, quizId, onClose }) => {
  const { createQuiz, updateQuiz } = useQuizStore();
  const [loading, setLoading] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set());

  const [formData, setFormData] = useState({
    title: '',
    passing_score: 60,
    questions: [] as QuestionFormData[],
  });

  useEffect(() => {
    // TODO: 如果编辑测验，加载测验数据
    // 这里需要从 store 或其他地方获取测验详情
  }, [quizId]);

  const handleAddQuestion = () => {
    const newQuestion: QuestionFormData = {
      question_text: '',
      question_type: 'single',
      correct_answer: '',
      explanation: '',
      order: formData.questions.length,
      options: [
        { option_text: '', option_index: 0 },
        { option_text: '', option_index: 1 },
        { option_text: '', option_index: 2 },
        { option_text: '', option_index: 3 },
      ],
    };
    setFormData((prev) => ({
      ...prev,
      questions: [...prev.questions, newQuestion],
    }));
    // 自动展开新问题
    setExpandedQuestions(new Set([...expandedQuestions, formData.questions.length]));
  };

  const handleUpdateQuestion = (index: number, updates: Partial<QuestionFormData>) => {
    setFormData((prev) => ({
      ...prev,
      questions: prev.questions.map((q, i) => (i === index ? { ...q, ...updates } : q)),
    }));
  };

  const handleDeleteQuestion = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      questions: prev.questions.filter((_, i) => i !== index),
    }));
  };

  const handleToggleExpand = (index: number) => {
    const newExpanded = new Set(expandedQuestions);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedQuestions(newExpanded);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const quizData: QuizCreate = {
        chapter_id: chapterId,
        title: formData.title,
        passing_score: formData.passing_score,
        questions: formData.questions.map((q) => ({
          question_text: q.question_text,
          question_type: q.question_type,
          correct_answer: q.correct_answer,
          explanation: q.explanation,
          options: q.options,
        })),
      };

      if (quizId) {
        await updateQuiz(quizId, { title: formData.title, passing_score: formData.passing_score });
        // TODO: 更新题目和选项
      } else {
        await createQuiz(quizData);
      }
      onClose();
    } catch (error) {
      console.error('保存失败:', error);
      alert('保存失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-8 overflow-y-auto">
      <div className="bg-slate-800 rounded-xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col my-8">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-xl font-bold text-white">
            {quizId ? '编辑测验' : '创建测验'}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6">
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                测验标题 *
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData((prev) => ({ ...prev, title: e.target.value }))}
                required
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                placeholder="章节测验"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                及格分数 (%)
              </label>
              <input
                type="number"
                value={formData.passing_score}
                onChange={(e) => setFormData((prev) => ({ ...prev, passing_score: parseInt(e.target.value) || 0 }))}
                min="0"
                max="100"
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Questions */}
            <div className="mt-8">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-white">题目列表</h3>
                <button
                  type="button"
                  onClick={handleAddQuestion}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 text-white rounded-lg transition-colors text-sm"
                >
                  + 添加题目
                </button>
              </div>

              <div className="space-y-4">
                {formData.questions.map((question, qIndex) => (
                  <QuestionEditor
                    key={qIndex}
                    index={qIndex}
                    question={question}
                    isExpanded={expandedQuestions.has(qIndex)}
                    onToggleExpand={() => handleToggleExpand(qIndex)}
                    onUpdate={(updates) => handleUpdateQuestion(qIndex, updates)}
                    onDelete={() => handleDeleteQuestion(qIndex)}
                  />
                ))}
              </div>
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-4 border-t border-slate-700 space-x-4">
          <button
            type="button"
            onClick={onClose}
            className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            type="submit"
            onClick={handleSubmit}
            disabled={loading || formData.questions.length === 0}
            className="px-6 py-2 bg-cyan-600 hover:bg-cyan-700 disabled:bg-slate-600 text-white rounded-lg transition-colors"
          >
            {loading ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  );
};

// 题目编辑器组件
interface QuestionEditorProps {
  index: number;
  question: QuestionFormData;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onUpdate: (updates: Partial<QuestionFormData>) => void;
  onDelete: () => void;
}

const QuestionEditor: React.FC<QuestionEditorProps> = ({
  index,
  question,
  isExpanded,
  onToggleExpand,
  onUpdate,
  onDelete,
}) => {
  const handleOptionChange = (optionIndex: number, value: string) => {
    onUpdate({
      options: question.options.map((opt, i) =>
        i === optionIndex ? { ...opt, option_text: value } : opt
      ),
    });
  };

  const handleCorrectAnswerChange = (optionIndex: number) => {
    const currentIndex = question.correct_answer.split(',').map(Number);
    let newIndex: number[];

    if (question.question_type === 'multiple') {
      // 多选题可以选多个
      if (currentIndex.includes(optionIndex)) {
        newIndex = currentIndex.filter((i) => i !== optionIndex);
      } else {
        newIndex = [...currentIndex, optionIndex];
      }
    } else {
      // 单选题只能选一个
      newIndex = [optionIndex];
    }

    onUpdate({ correct_answer: newIndex.join(',') });
  };

  const optionsLabels = ['A', 'B', 'C', 'D', 'E', 'F'];

  return (
    <div className="bg-slate-700/50 rounded-lg border border-slate-600 overflow-hidden">
      {/* Question Header */}
      <div className="flex items-center justify-between p-4 cursor-pointer" onClick={onToggleExpand}>
        <div className="flex items-center space-x-3">
          <span className="text-slate-400 font-medium">题目 {index + 1}</span>
          <span className="text-xs px-2 py-1 bg-slate-600 rounded">
            {question.question_type === 'single' ? '单选题' :
             question.question_type === 'multiple' ? '多选题' : '判断题'}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          <svg
            className={`w-5 h-5 text-slate-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="text-red-400 hover:text-red-300 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Question Content */}
      {isExpanded && (
        <div className="p-4 border-t border-slate-600 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              题目类型
            </label>
            <select
              value={question.question_type}
              onChange={(e) => onUpdate({
                question_type: e.target.value as 'single' | 'multiple' | 'true_false',
                correct_answer: ''
              })}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
            >
              <option value="single">单选题</option>
              <option value="multiple">多选题</option>
              <option value="true_false">判断题</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              题目内容 *
            </label>
            <textarea
              value={question.question_text}
              onChange={(e) => onUpdate({ question_text: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              placeholder="请输入题目内容"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              选项和正确答案 *
            </label>
            <div className="space-y-2">
              {question.options.map((option, optIndex) => (
                <div key={optIndex} className="flex items-center space-x-3">
                  <input
                    type={question.question_type === 'multiple' ? 'checkbox' : 'radio'}
                    checked={question.correct_answer.split(',').map(Number).includes(optIndex)}
                    onChange={() => handleCorrectAnswerChange(optIndex)}
                    className="w-4 h-4"
                  />
                  <span className="text-slate-400 w-6">{optionsLabels[optIndex]}.</span>
                  <input
                    type="text"
                    value={option.option_text}
                    onChange={(e) => handleOptionChange(optIndex, e.target.value)}
                    className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
                    placeholder={`选项 ${optionsLabels[optIndex]} 的内容`}
                  />
                </div>
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-2">勾选正确的答案</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              答案解析
            </label>
            <textarea
              value={question.explanation}
              onChange={(e) => onUpdate({ explanation: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-cyan-500"
              placeholder="请解释为什么这个答案是正确的"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default QuizForm;
