'use client';
import {T} from '@/components/LocalizedText';


import { useUser } from '@/lib/UserContext';
import React, { useState, useEffect } from 'react';
import {
  getDashboardMetrics,
  getQuadrantItems,
  getExportCsvUrl,
  getExportJsonUrl
} from '@/lib/api';
import { PerformanceMetrics, QuadrantItem } from '@/lib/types';
import {
  BarChart3,
  CheckCircle2,
  XCircle,
  BrainCircuit,
  TrendingUp,
  FileSpreadsheet,
  FileCode,
  Tag
} from 'lucide-react';

export default function DashboardPage() {
  const {user}=useUser();
  const [error, setError] = useState('');
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeQuadrant, setActiveQuadrant] = useState<string>('ALL');
  const [quadrantItems, setQuadrantItems] = useState<QuadrantItem[]>([]);
  const [loadingItems, setLoadingItems] = useState(false);

  useEffect(() => {
    getDashboardMetrics()
      .then(setMetrics)
      .catch(e => setError(e instanceof Error ? e.message : 'Could not load insights.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setLoadingItems(true);
    getQuadrantItems(activeQuadrant)
      .then(setQuadrantItems)
      .catch(e => setError(e instanceof Error ? e.message : 'Could not load insights.'))
      .finally(() => setLoadingItems(false));
  }, [activeQuadrant]);

  if (loading) {
    return <div className="text-center py-16 text-slate-500 text-sm"><T text="Loading research insights…" /></div>;
  }

  return (
    <div className="space-y-8 py-2">
      {error&&<p className="error-box" role="alert"><T>{error}</T> <button className="text-link" onClick={()=>location.reload()}><T text="Try again" /></button></p>}
      {/* Header & Export Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 border border-brand-200/80 text-brand-700 text-xs font-semibold">
            <BarChart3 className="w-3.5 h-3.5" />
            <span><T text="Recorded research results" /></span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight mt-1">{" "}<T text="Research Insights" />{" "}</h1>
          <p className="text-slate-600 text-sm">{" "}<T text="Compare recorded participant answers with model predictions." />{" "}</p>
        </div>

        {/* Thesis Export Buttons */}
        {user?.role !== "participant" && <div className="flex items-center gap-2.5">
          <a
            href={getExportCsvUrl()}
            download
            className="px-3.5 py-2 rounded-xl glass-panel hover:bg-white text-slate-700 hover:text-slate-900 font-semibold text-xs flex items-center gap-1.5 transition-all border border-slate-200/80 shadow-xs"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
            <span><T text="Export CSV" /></span>
          </a>
          <a
            href={getExportJsonUrl()}
            download
            className="px-3.5 py-2 rounded-xl glass-panel hover:bg-white text-slate-700 hover:text-slate-900 font-semibold text-xs flex items-center gap-1.5 transition-all border border-slate-200/80 shadow-xs"
          >
            <FileCode className="w-4 h-4 text-brand-600" />
            <span><T text="Export JSON" /></span>
          </a>
        </div>}
      </div>

      {metrics && (
        <>
          {/* Top Performance Comparison KPI Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Evaluations */}
            <div className="glass-panel p-5 rounded-3xl space-y-1">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">{" "}<T text="Total Evaluations" />{" "}</span>
              <p className="text-3xl font-extrabold text-slate-900 font-mono">
                {metrics.total_evaluations}
              </p>
              <p className="text-[11px] text-slate-500"><T text="Total recorded trials" /></p>
            </div>

            {/* Human Accuracy */}
            <div className="glass-panel p-5 rounded-3xl space-y-1">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">{" "}<T text="Human Accuracy" />{" "}</span>
              <p className="text-3xl font-extrabold text-emerald-600 font-mono">
                {metrics.human_accuracy}%
              </p>
              <p className="text-[11px] text-slate-500">{" "}<T text="Precision:" />{" "}{metrics.human_precision}% &bull; F1: {metrics.human_f1}%
              </p>
            </div>

            {/* AI Detector Accuracy */}
            <div className="glass-panel p-5 rounded-3xl space-y-1">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">{" "}<T text="Swin + DCT + Transformer Accuracy" />{" "}</span>
              <p className="text-3xl font-extrabold text-brand-700 font-mono">
                {metrics.ai_accuracy}%
              </p>
              <p className="text-[11px] text-slate-500">{" "}<T text="Precision:" />{" "}{metrics.ai_precision}% &bull; F1: {metrics.ai_f1}%
              </p>
            </div>

            {/* Hybrid Ensemble */}
            <div className="glass-panel-glow p-5 rounded-3xl space-y-1">
              <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider">{" "}<T text="Experimental rule (Human + AI)" />{" "}</span>
              <p className="text-3xl font-extrabold text-indigo-700 font-mono">
                {metrics.hybrid_accuracy}%
              </p>
              <p className="text-[11px] text-slate-500"><T text="Complementary decision rule" /></p>
            </div>
          </div>

          {/* Confusion Matrices & Calibration */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Human Confusion Matrix */}
            <div className="lg:col-span-4 glass-panel p-6 sm:p-7 rounded-3xl space-y-4">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">{" "}<T text="Human Confusion Matrix" />{" "}</h3>
              <div className="grid grid-cols-2 gap-2.5 text-center text-xs">
                <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200">
                  <p className="text-[10px] text-emerald-800 font-medium"><T text="True Positives (Fake)" /></p>
                  <p className="text-xl font-mono font-bold text-slate-900 mt-1">
                    {metrics.human_confusion_matrix.TP}
                  </p>
                </div>
                <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200">
                  <p className="text-[10px] text-rose-800 font-medium"><T text="False Positives (Type I)" /></p>
                  <p className="text-xl font-mono font-bold text-slate-900 mt-1">
                    {metrics.human_confusion_matrix.FP}
                  </p>
                </div>
                <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200">
                  <p className="text-[10px] text-rose-800 font-medium"><T text="False Negatives (Type II)" /></p>
                  <p className="text-xl font-mono font-bold text-slate-900 mt-1">
                    {metrics.human_confusion_matrix.FN}
                  </p>
                </div>
                <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200">
                  <p className="text-[10px] text-emerald-800 font-medium"><T text="True Negatives (Real)" /></p>
                  <p className="text-xl font-mono font-bold text-slate-900 mt-1">
                    {metrics.human_confusion_matrix.TN}
                  </p>
                </div>
              </div>
            </div>

            {/* AI Confusion Matrix */}
            <div className="lg:col-span-4 glass-panel p-6 sm:p-7 rounded-3xl space-y-4">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">{" "}<T text="Swin + DCT + Transformer Confusion Matrix" />{" "}</h3>
              <div className="grid grid-cols-2 gap-2.5 text-center text-xs">
                <div className="p-4 rounded-2xl bg-brand-50 border border-brand-200">
                  <p className="text-[10px] text-brand-800 font-medium"><T text="True Positives (Fake)" /></p>
                  <p className="text-xl font-mono font-bold text-slate-900 mt-1">
                    {metrics.ai_confusion_matrix.TP}
                  </p>
                </div>
                <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200">
                  <p className="text-[10px] text-rose-800 font-medium"><T text="False Positives (Type I)" /></p>
                  <p className="text-xl font-mono font-bold text-slate-900 mt-1">
                    {metrics.ai_confusion_matrix.FP}
                  </p>
                </div>
                <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200">
                  <p className="text-[10px] text-rose-800 font-medium"><T text="False Negatives (Type II)" /></p>
                  <p className="text-xl font-mono font-bold text-slate-900 mt-1">
                    {metrics.ai_confusion_matrix.FN}
                  </p>
                </div>
                <div className="p-4 rounded-2xl bg-brand-50 border border-brand-200">
                  <p className="text-[10px] text-brand-800 font-medium"><T text="True Negatives (Real)" /></p>
                  <p className="text-xl font-mono font-bold text-slate-900 mt-1">
                    {metrics.ai_confusion_matrix.TN}
                  </p>
                </div>
              </div>
            </div>

            {/* Calibration Curve Data */}
            <div className="lg:col-span-4 glass-panel p-6 sm:p-7 rounded-3xl space-y-4">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-600" />
                <span><T text="Confidence Calibration" /></span>
              </h3>
              <div className="space-y-2.5">
                {metrics.calibration_data.map((c) => (
                  <div key={c.confidence_level} className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-slate-600 font-medium">{c.confidence_label}</span>
                      <span className="font-mono text-emerald-700 font-bold">
                        {c.actual_accuracy}<T text="% Acc (" />{c.sample_count}{" "}<T text="samples)" />{" "}</span>
                    </div>
                    <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        style={{ width: `${c.actual_accuracy}%` }}
                        className="h-full bg-emerald-500 rounded-full transition-all"
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {/* 4-Quadrant Disagreement Explorer */}
      <div className="glass-panel p-6 sm:p-8 rounded-3xl space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-brand-600" />
              <span><T text="4-Quadrant Disagreement Explorer" /></span>
            </h3>
            <p className="text-slate-500 text-xs">{" "}<T text="Isolate trials to analyze why the AI model failed on specific artifacts that humans caught." />{" "}</p>
          </div>

          {/* Quadrant Filter Pills */}
          <div className="flex flex-wrap gap-2">
            {[
              { code: 'ALL', label: 'All Trials' },
              { code: 'Q1', label: 'Q1: Consensus Correct' },
              { code: 'Q2', label: 'Q2: Model Blindspot (Human+ AI-)' },
              { code: 'Q3', label: 'Q3: Human Limit (Human- AI+)' },
              { code: 'Q4', label: 'Q4: Frontier Edge (Human- AI-)' },
            ].map((q) => {
              const isSelected = activeQuadrant === q.code;
              return (
                <button
                  key={q.code}
                  onClick={() => setActiveQuadrant(q.code)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border ${
                    isSelected
                      ? 'bg-brand-600 border-brand-600 text-white shadow-xs'
                      : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {q.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Quadrant Items List */}
        {loadingItems ? (
          <p className="text-xs muted py-6 text-center"><T text="Filtering trials..." /></p>
        ) : quadrantItems.length === 0 ? (
          <p className="text-xs muted py-6 text-center"><T text="No trials found for this quadrant filter." /></p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {quadrantItems.map((item) => (
              <div
                key={item.submission_id}
                className="p-5 rounded-2xl bg-white border border-slate-200/80 space-y-3 shadow-xs hover:border-brand-400/80 transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-slate-900">{item.title}</span>
                  <span
                    className={`px-2 py-0.5 rounded-md text-[10px] font-bold font-mono uppercase ${
                      item.disagreement_quadrant === 'Q1'
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : item.disagreement_quadrant === 'Q2'
                        ? 'bg-amber-50 text-amber-800 border border-amber-200'
                        : item.disagreement_quadrant === 'Q3'
                        ? 'bg-brand-50 text-brand-800 border border-brand-200'
                        : 'bg-purple-50 text-purple-800 border border-purple-200'
                    }`}
                  >
                    {item.disagreement_quadrant}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 space-y-0.5">
                    <p className="text-[10px] text-slate-500 font-medium"><T text="Human Judgment" /></p>
                    <p className="font-bold text-slate-900 flex items-center gap-1">
                      {item.human_prediction}{' '}
                      {item.is_human_correct ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-rose-600" />
                      )}
                    </p>
                    <p className="text-[10px] muted">{" "}<T text="Conf: Level" />{" "}{item.human_confidence}/5 &bull; {item.reaction_time_ms}<T text="ms" />{" "}</p>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 space-y-0.5">
                    <p className="text-[10px] text-slate-500 font-medium"><T text="Swin + DCT + Transformer Detector" /></p>
                    <p className="font-bold text-slate-900 flex items-center gap-1">
                      {item.ai_prediction}{' '}
                      {item.is_ai_correct ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <XCircle className="w-3.5 h-3.5 text-rose-600" />
                      )}
                    </p>
                    <p className="text-[10px] muted"><T text="Conf:" />{" "}{item.ai_confidence}%</p>
                  </div>
                </div>

                {item.clue_tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 items-center pt-1">
                    <Tag className="w-3 h-3 muted mr-1" />
                    {item.clue_tags.map((tag, tIdx) => (
                      <span
                        key={tIdx}
                        className="text-[10px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
