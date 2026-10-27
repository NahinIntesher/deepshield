'use client';
import {useLocale} from '@/lib/Locale';

import {T} from '@/components/LocalizedText';
import DetectionExplanation from '@/components/DetectionExplanation';


import React, { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useUser } from '@/lib/UserContext';
import { getResearchItems, submitResearchEvaluation, getMediaUrl } from '@/lib/api';
import { ResearchItem, ResearchSubmissionResult } from '@/lib/types';
import {
  Microscope,
  CheckCircle2,
  XCircle,
  BrainCircuit,
  ArrowRight,
  Lock,
  Unlock,
  Tag
} from 'lucide-react';

const CLUE_OPTIONS = [
  'Blinking/Eyes',
  'Mouth/Teeth',
  'Face Boundary',
  'Lighting/Shadows',
  'Audio/Video Desync',
  'None/Looks Natural'
];

export default function ResearchPage() {const {t}=useLocale();
  const { user } = useUser();
  const [error, setError] = useState('');
  const [items, setItems] = useState<ResearchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Human Protocol Inputs
  const [humanVerdict, setHumanVerdict] = useState<'Real' | 'Fake' | null>(null);
  const [humanConfidence, setHumanConfidence] = useState<number>(3); // 1 to 5
  const [selectedClues, setSelectedClues] = useState<string[]>([]);
  const [submissionResult, setSubmissionResult] = useState<ResearchSubmissionResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [heatmapOpacity, setHeatmapOpacity] = useState(70);

  const startTimeRef = useRef<number>(Date.now());

  useEffect(() => {
    if (user && (user.qualified_for_research)) {
      setLoading(true);
      getResearchItems(user.id)
        .then((data) => {
          setItems(data);
          startTimeRef.current = Date.now();
        })
        .catch(e => setError(e instanceof Error ? e.message : 'Could not load research videos.'))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [user]);

  const toggleClue = (clue: string) => {
    setSelectedClues((prev) =>
      prev.includes(clue) ? prev.filter((c) => c !== clue) : [...prev, clue]
    );
  };

  const handleSubmitEvaluation = async () => {
    if (!user || !humanVerdict || !items[currentIndex]) return;
    const reactionTime = Date.now() - startTimeRef.current;
    setError('');
    setSubmitting(true);

    try {
      const res = await submitResearchEvaluation(
        user.id,
        items[currentIndex].id,
        humanVerdict,
        humanConfidence,
        selectedClues,
        reactionTime
      );
      setSubmissionResult(res);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Evaluation failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextItem = () => {
    setHumanVerdict(null);
    setHumanConfidence(3);
    setSelectedClues([]);
    setSubmissionResult(null);
    setItems(prev=>prev.filter(item=>item.id!==items[currentIndex]?.id));
    setCurrentIndex(0);
    startTimeRef.current = Date.now();
  };

  if (error && !items.length) return <section className="card" role="alert"><h1><T text="Research could not load" /></h1><p className="error-box"><T>{error}</T></p><button className="secondary-button mt-4" onClick={()=>location.reload()}><T text="Try again" /></button></section>;

  // If user has not qualified and is in participant mode
  if (!user?.qualified_for_research) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
        <div className="w-16 h-16 rounded-3xl bg-amber-50 border border-amber-200/80 text-amber-600 mx-auto flex items-center justify-center shadow-xs">
          <Lock className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-3xl font-extrabold text-slate-900"><T text="Research Challenge Locked" /></h2>
          <p className="text-slate-600 text-sm max-w-md mx-auto leading-relaxed">{" "}<T text="The Research Challenge is an academic data-collection experiment reserved for top-performing participants. Achieve" />{" "}<strong><T text="≥ 90% accuracy" /></strong>{" "}<T text="and" />{" "}<strong><T text="at least 5,000 points" /></strong>{" "}<T text="in the Real vs Fake game. Your current target and progress are shown in the arena." />{" "}</p>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-3.5 pt-4">
          <Link
            href="/play"
            className="px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md shadow-emerald-500/20 transition-all"
          >{" "}<T text="Play Real vs Fake to Qualify" />{" "}</Link>


        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="text-center py-16 text-slate-500 text-sm"><T text="Loading Research Challenge Items..." /></div>;
  }

  const currentItem = items[currentIndex];
  if (!currentItem) {
    return <div className="text-center py-16 text-slate-500 text-sm"><T text="No research items available." /></div>;
  }

  return (
    <div className="space-y-8 py-2">
      {error&&<p className="error-box" role="alert"><T>{error}</T></p>}
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-50 border border-brand-200/80 text-brand-700 text-xs font-semibold">
            <Microscope className="w-3.5 h-3.5" />
            <span><T text="Research Challenge" /></span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight mt-1">{" "}<T text="Research Challenge Item #" />{currentIndex + 1}{" "}<T text="of" />{" "}{items.length}
          </h1>
          <p className="text-slate-600 text-sm">{" "}<T text="Watch the video and record your answer, confidence and observed clues. Then compare your answer with the model." />{" "}</p>
        </div>

        <Link
          href="/dashboard"
          className="px-4 py-2 rounded-xl glass-panel hover:bg-white text-brand-700 font-semibold text-xs flex items-center gap-2 transition-all self-start sm:self-center border border-slate-200/80"
        >
          <span><T text="View Research Dashboard" /></span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Media Inspection Viewer */}
        <div className="lg:col-span-6 space-y-4">
          <div className="glass-panel p-6 sm:p-7 rounded-3xl space-y-4">
            <div className="aspect-video w-full rounded-2xl overflow-hidden bg-slate-900 border border-slate-200 relative flex items-center justify-center shadow-xs">
              <video key={currentItem.id} controls playsInline preload="metadata"
 src={getMediaUrl(currentItem.media_url)}
 aria-label={currentItem.title}
                className="w-full h-full object-contain"
              />
              <div className="absolute top-3 left-3 px-2.5 py-1 rounded-md bg-white/90 border border-slate-200 text-[10px] text-slate-800 font-mono shadow-xs">
                {t(currentItem.difficulty)} &bull; <T>{currentItem.manipulation_type}</T>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-900">{currentItem.title}</h3>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">{currentItem.description}</p>
            </div>
          </div>
        </div>

        {/* Right: Human Input Protocol OR Human-AI Comparison Reveal */}
        <div className="lg:col-span-6">
          {!submissionResult ? (
            /* Human Evaluation Form */
            <div className="glass-panel p-6 sm:p-8 rounded-3xl space-y-6">
              <h3 className="text-base font-bold text-slate-900 uppercase tracking-wider">{" "}<T text="Your assessment" />{" "}</h3>

              {/* Step 1: Verdict */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-700">{" "}<T text="Step 1: Your Verdict (Is this media Real or Fake?)" />{" "}</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    aria-pressed={humanVerdict==='Real'} disabled={submitting} onClick={() => setHumanVerdict('Real')}
                    className={`py-3.5 rounded-2xl border font-bold text-sm transition-all ${
                      humanVerdict === 'Real'
                        ? 'bg-emerald-600 border-emerald-600 text-white shadow-md shadow-emerald-500/20'
                        : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-700'
                    }`}
                  >{" "}<T text="REAL" />{" "}</button>
                  <button
                    aria-pressed={humanVerdict==='Fake'} disabled={submitting} onClick={() => setHumanVerdict('Fake')}
                    className={`py-3.5 rounded-2xl border font-bold text-sm transition-all ${
                      humanVerdict === 'Fake'
                        ? 'bg-rose-600 border-rose-600 text-white shadow-md shadow-rose-500/20'
                        : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-700'
                    }`}
                  >{" "}<T text="FAKE" />{" "}</button>
                </div>
              </div>

              {/* Step 2: Confidence Rating (1 to 5) */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-700">{" "}<T text="Step 2: How confident are you?" />{" "}</span>
                  <span className="font-mono text-brand-700 font-bold"><T text="Level" />{" "}{humanConfidence}/5</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="5"
                  step="1"
                  value={humanConfidence}
                  onChange={(e) => setHumanConfidence(Number(e.target.value))}
                  aria-label={t('Your confidence','আপনি কতটা নিশ্চিত')} className="w-full accent-blue-600"
                />
                <div className="flex justify-between text-[10px] muted">
                  <span><T text="1 (Pure Guess)" /></span>
                  <span><T text="3 (Moderate)" /></span>
                  <span><T text="5 (Absolute Certainty)" /></span>
                </div>
              </div>

              {/* Step 3: Observed Artifact Cues */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-700 flex items-center gap-1.5">
                  <Tag className="w-3.5 h-3.5 text-brand-600" />
                  <span><T text="Step 3: What clues tipped you off? (Select all that apply)" /></span>
                </label>
                <div className="flex flex-wrap gap-2">
                  {CLUE_OPTIONS.map((clue) => {
                    const isSelected = selectedClues.includes(clue);
                    return (
                      <button
                        key={t(clue)}
                        type="button"
                        aria-pressed={isSelected} disabled={submitting} onClick={() => toggleClue(clue)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all border ${
                          isSelected
                            ? 'bg-brand-600 text-white border-brand-600 shadow-xs'
                            : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-700'
                        }`}
                      >
                        {t(clue)}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Submit Button */}
              <button
                onClick={handleSubmitEvaluation}
                disabled={!humanVerdict || submitting}
                className="w-full py-3.5 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-bold text-xs shadow-md shadow-brand-500/20 transition-all flex items-center justify-center gap-2"
              >
                <span><T>{submitting ? 'Comparing…' : 'Compare with model'}</T></span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          ) : (
            /* Human vs AI Evaluation Breakdown */
            <div className="glass-panel p-6 sm:p-8 rounded-3xl space-y-6">
              {/* 4-Quadrant Badge */}
              <div
                className={`p-4 rounded-2xl border flex items-center justify-between ${
                  submissionResult.disagreement_quadrant === 'Q1'
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
                    : submissionResult.disagreement_quadrant === 'Q2'
                    ? 'bg-amber-50 border-amber-300 text-amber-950'
                    : submissionResult.disagreement_quadrant === 'Q3'
                    ? 'bg-brand-50 border-brand-300 text-brand-950'
                    : 'bg-purple-50 border-purple-300 text-purple-950'
                }`}
              >
                <div className="space-y-0.5">
                  <span className="font-mono text-xs font-extrabold uppercase tracking-wider">
                    {submissionResult.disagreement_quadrant}{" "}<T text="DISAGREEMENT QUADRANT" />{" "}</span>
                  <h4 className="font-bold text-slate-900 text-base">
                    <T>{submissionResult.quadrant_description}</T>
                  </h4>
                </div>
                <span className="text-xs font-bold px-2 py-1 rounded-md bg-white border border-slate-200 text-slate-800 shadow-xs">{t('Dataset label:','ডেটাসেটের উত্তর:')} <T>{submissionResult.ground_truth}</T>
                </span>
              </div>

              {/* Side-by-Side Comparison Grid */}
              <div className="grid grid-cols-2 gap-4">
                {/* Human Card */}
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-500"><T text="Human Evaluator" /></span>
                    {submissionResult.is_human_correct ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-600" />
                    )}
                  </div>
                  <p className="text-xl font-extrabold text-slate-900">
                    <T>{submissionResult.human_prediction}</T>
                  </p>
                  <p className="text-[11px] text-slate-500">{" "}<T text="Confidence: Level" />{" "}{submissionResult.human_confidence}/5
                  </p>
                </div>

                {/* AI Model Card */}
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-500"><T text="Swin + DCT + Transformer Detector" /></span>
                    {submissionResult.is_ai_correct ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <XCircle className="w-4 h-4 text-rose-600" />
                    )}
                  </div>
                  <p className="text-xl font-extrabold text-slate-900">
                    <T>{submissionResult.ai_prediction}</T>
                  </p>
                  <p className="text-[11px] text-slate-500">{t('Model score:','মডেলের স্কোর:')} {Math.round(submissionResult.ai_confidence * 100)}%
                  </p>
                </div>
              </div>

              {/* Explainable AI Disagreement Diagnosis */}
              <div className="p-4 rounded-2xl bg-brand-50/70 border border-brand-200/80 space-y-2">
                <h4 className="text-xs font-bold text-brand-900 flex items-center gap-1.5 uppercase">
                  <BrainCircuit className="w-4 h-4 text-brand-600" />
                  <span>{t('How your answers compare','আপনার উত্তর ও মডেলের ফল')}</span>
                </h4>
                <p className="text-xs text-brand-950 leading-relaxed">
                  {submissionResult.disagreement_quadrant==='Q1'?t('Your answer and the model’s answer both match the dataset label.','আপনার উত্তর ও মডেলের ফল—দুটিই ডেটাসেটের উত্তরের সঙ্গে মিলেছে।'):submissionResult.disagreement_quadrant==='Q2'?t('Your answer matches the dataset label. The model’s answer does not.','আপনার উত্তর ডেটাসেটের উত্তরের সঙ্গে মিলেছে। মডেলের ফল মেলেনি।'):submissionResult.disagreement_quadrant==='Q3'?t('The model’s answer matches the dataset label. Your answer does not.','মডেলের ফল ডেটাসেটের উত্তরের সঙ্গে মিলেছে। আপনার উত্তর মেলেনি।'):t('Neither answer matches the dataset label.','আপনার উত্তর ও মডেলের ফল—কোনোটিই ডেটাসেটের উত্তরের সঙ্গে মেলেনি।')}
                  {' '}{t('This comparison does not establish why an answer was wrong.','এই তুলনা থেকে ভুলের কারণ নিশ্চিতভাবে জানা যায় না।')}
                </p>
              </div>

              {/* Spatial Patch Heatmap */}
              {!submissionResult.analysis && submissionResult.xai_heatmap_url && (
                <div className="glass-panel p-4 rounded-2xl space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900"><T text="Input-gradient Sensitivity Heatmap" /></span>
                    <div className="flex items-center gap-1 text-[11px] text-slate-600">
                      <span><T text="Opacity:" /></span>
                      <input
                        type="range"
                        min="10"
                        max="100"
                        value={heatmapOpacity}
                        onChange={(e) => setHeatmapOpacity(Number(e.target.value))}
                        className="w-16 accent-blue-600"
                      />
                    </div>
                  </div>
                  <div className="aspect-square max-w-[200px] mx-auto rounded-xl overflow-hidden bg-slate-900 border border-slate-200 shadow-xs">
                    <img
                      src={submissionResult.xai_heatmap_url}
                      alt={t("Heatmap")}
                      style={{ opacity: heatmapOpacity / 100 }}
                      className="w-full h-full object-contain"
                    />
                  </div>
                </div>
              )}

            </div>
          )}
        </div>
      </div>
      {submissionResult?.analysis && <DetectionExplanation result={submissionResult.analysis}/>}
      {submissionResult && <button type="button" onClick={handleNextItem} className="primary-button w-full sm:w-auto">{t('Continue to the next video','পরের ভিডিওতে যান')}<ArrowRight size={18}/></button>}
    </div>
  );
}
