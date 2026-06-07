import { useState } from 'react'
import styles from './QuizCard.module.css'

export interface QuizQuestion {
  n: number
  q: string
  choices: Record<string, string>  // { a: '...', b: '...', c: '...', d: '...' }
  correct: string                   // 'a' | 'b' | 'c' | 'd'
}

export interface QuizData {
  total: number
  questions: QuizQuestion[]
}

interface QuizCardProps {
  data: QuizData
  onSubmitAnswers?: (summary: string) => void
}

export function QuizCard({ data, onSubmitAnswers }: QuizCardProps) {
  const [current, setCurrent] = useState(0)
  const [answers, setAnswers] = useState<Record<number, string>>({})
  const [revealed, setRevealed] = useState(false)

  const q = data.questions[current]
  const allAnswered = Object.keys(answers).length === data.total
  const score = revealed
    ? data.questions.filter(qu => answers[qu.n] === qu.correct).length
    : null

  function handleSelect(letter: string) {
    if (revealed) return
    setAnswers(prev => ({ ...prev, [q.n]: letter }))
  }

  function handleReveal() {
    setRevealed(true)
    const sc = data.questions.filter(qu => answers[qu.n] === qu.correct).length
    const lines = data.questions.map(qu => {
      const userAns = answers[qu.n]
      const isRight = userAns === qu.correct
      const userText = userAns ? `${userAns}) ${qu.choices[userAns]}` : '(skipped)'
      const correctHint = !isRight ? ` *(correct: ${qu.correct}) ${qu.choices[qu.correct]})*` : ''
      return `- **Q${qu.n}** ${isRight ? '✅' : '❌'} ${userText}${correctHint}`
    })
    onSubmitAnswers?.(
      `Quiz results: **${sc}/${data.total}** correct\n\n` + lines.join('\n')
    )
  }

  return (
    <div className={styles.card}>
      {/* Dot progress bar */}
      <div className={styles.progress}>
        {data.questions.map((qu, i) => {
          const ans = answers[qu.n]
          let cls = styles.dot
          if (revealed && ans) cls = ans === qu.correct ? `${styles.dot} ${styles.dotCorrect}` : `${styles.dot} ${styles.dotWrong}`
          else if (ans) cls = `${styles.dot} ${styles.dotAnswered}`
          return (
            <button
              key={i}
              className={`${cls}${i === current ? ` ${styles.dotActive}` : ''}`}
              onClick={() => setCurrent(i)}
              aria-label={`Go to question ${i + 1}`}
            />
          )
        })}
        {revealed && score !== null && (
          <span className={styles.scoreBadge}>{score}/{data.total} ★</span>
        )}
      </div>

      {/* Question */}
      <div className={styles.question}>
        <span className={styles.qNum}>Question {q.n} of {data.total}</span>
        <p className={styles.qText}>{q.q}</p>
      </div>

      {/* Choices */}
      <div className={styles.choices}>
        {Object.entries(q.choices).map(([letter, text]) => {
          const selected = answers[q.n] === letter
          let cls = styles.choice
          if (revealed) {
            if (letter === q.correct) cls = `${styles.choice} ${styles.choiceCorrect}`
            else if (selected) cls = `${styles.choice} ${styles.choiceWrong}`
          } else if (selected) {
            cls = `${styles.choice} ${styles.choiceSelected}`
          }
          return (
            <button
              key={letter}
              className={cls}
              onClick={() => handleSelect(letter)}
              disabled={revealed}
            >
              <span className={styles.choiceLetter}>{letter}</span>
              <span>{text}</span>
            </button>
          )
        })}
      </div>

      {/* Navigation */}
      <div className={styles.nav}>
        <button
          className={styles.navBtn}
          onClick={() => setCurrent(c => Math.max(0, c - 1))}
          disabled={current === 0}
        >
          ← Prev
        </button>

        {!revealed && allAnswered && (
          <button className={styles.submitBtn} onClick={handleReveal}>
            Check Answers
          </button>
        )}
        {!revealed && !allAnswered && (
          <span className={styles.hint}>
            {Object.keys(answers).length}/{data.total} answered
          </span>
        )}

        <button
          className={styles.navBtn}
          onClick={() => setCurrent(c => Math.min(data.total - 1, c + 1))}
          disabled={current === data.total - 1}
        >
          Next →
        </button>
      </div>
    </div>
  )
}
