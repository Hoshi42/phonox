import styles from './VinylSpinner.module.css'

interface VinylSpinnerProps {
  message?: string
  subtext?: string
}

export default function VinylSpinner({ 
  message, 
  subtext
}: VinylSpinnerProps) {
  return (
    <div className={styles.spinnerContainer}>
      <div className={styles.vinylRecord}>
        <img 
          src="/phonox.png" 
          alt="Phonox vinyl record icon" 
          className={styles.vinylImage}
        />
      </div>
      
      {message && <p className={styles.text}>{message}</p>}
      {subtext && <p className={styles.subtext}>{subtext}</p>}
    </div>
  )
}
