import { motion } from 'framer-motion';
import { useAuth } from '../../hooks/useAuth';

interface ProfileModalProps {
  onClose: () => void;
}

export const ProfileModal = ({ onClose }: ProfileModalProps) => {
  const { user } = useAuth();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <motion.div
        className="w-full max-w-md rounded-xl frosted-glass p-6 shadow-2xl"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
      >
        <h2 className="text-xl font-semibold text-text-dark">Edit Profile</h2>
        
        <form className="mt-6 space-y-4">
          <div>
            <label className="block mb-1 text-sm font-medium text-text-light">Full Name</label>
            <input 
              type="text"
              defaultValue={user?.name || ''}
              readOnly // Make this field read-only
              className="w-full p-2 bg-gray-100 rounded border border-border-light text-text-dark cursor-not-allowed" 
            />
          </div>
          <div>
            <label className="block mb-1 text-sm font-medium text-text-light">Email</label>
            <input 
              type="email"
              readOnly
              value={user?.email || ''}
              className="w-full p-2 bg-gray-100 rounded border border-border-light text-text-light cursor-not-allowed" 
            />
          </div>
          <div>
            <label className="block mb-1 text-sm font-medium text-text-light">Password</label>
            <input 
              type="password"
              placeholder="••••••••"
              readOnly // Make this field read-only
              className="w-full p-2 bg-gray-100 rounded border border-border-light text-text-dark cursor-not-allowed" 
            />
          </div>

          <div className="mt-6 flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-border-light bg-white/50 px-4 py-2 text-sm font-medium text-text-dark hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="button" // Change to type="button" since it's disabled
              disabled // Disable the save button
              className="rounded-lg bg-primary/50 px-4 py-2 text-sm font-medium text-white cursor-not-allowed"
            >
              Save Changes (Locked)
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};