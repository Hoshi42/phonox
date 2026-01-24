import styles from './LoadingSpinner.module.css'

export default function LoadingSpinner() {
  return (
    <div className={styles.spinnerContainer}>
      <div className={styles.spinner}></div>
      <p className={styles.text}>Analyzing vinyl records...</p>
      <p className={styles.subtext}>This usually takes 15-30 seconds</p>
    </div>
  )
}
