import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'

/** Bottom-Sheet: auf dem Handy von unten, am Desktop als zentrierter Dialog. */
export default function Sheet({ offen, onSchliessen, titel, children }) {
  return (
    <AnimatePresence>
      {offen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-end justify-center bg-zinc-900/40 backdrop-blur-[2px] sm:items-center sm:p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onSchliessen}
        >
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label={titel}
            className="flex max-h-[85dvh] w-full max-w-lg flex-col rounded-t-3xl bg-white shadow-2xl sm:rounded-3xl"
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ type: 'spring', damping: 28, stiffness: 320 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-zinc-100 px-5 py-4">
              <h3 className="font-semibold">{titel}</h3>
              <button onClick={onSchliessen} className="rounded-full p-1.5 text-zinc-500 hover:bg-zinc-100" aria-label="Schliessen">
                <X className="size-5" />
              </button>
            </div>
            <div className="overflow-y-auto p-5">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
