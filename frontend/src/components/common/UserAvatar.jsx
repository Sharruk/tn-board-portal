import { useState, useEffect } from 'react'

const SIZE_MAP = {
  xs: 'w-6 h-6 text-[10px]',
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
  xl: 'w-20 h-20 sm:w-24 sm:h-24 text-3xl font-black',
}

/**
 * Universal Avatar component that renders Google profile photo with:
 *   - referrerPolicy="no-referrer" (prevents Google CDN 403 blocks)
 *   - Graceful onError fallback to sleek initial avatar
 *   - Clean sizing and border options
 */
export default function UserAvatar({
  user,
  src,
  name,
  email,
  size = 'md',
  className = '',
  alt,
}) {
  const [imgError, setImgError] = useState(false)

  const photoUrl = src || user?.photoURL || user?.photo_url || null
  const displayName = name || user?.displayName || user?.display_name || user?.email || email || 'User'
  const initial = (displayName.trim()[0] || 'U').toUpperCase()
  const altText = alt || displayName

  useEffect(() => {
    setImgError(false)
  }, [photoUrl])

  const sizeClass = SIZE_MAP[size] || size

  if (photoUrl && !imgError) {
    return (
      <img
        src={photoUrl}
        alt={altText}
        referrerPolicy="no-referrer"
        crossOrigin="anonymous"
        onError={() => setImgError(true)}
        className={`${sizeClass} rounded-full object-cover shrink-0 select-none ${className}`}
      />
    )
  }

  return (
    <div
      className={`${sizeClass} rounded-full bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 text-white font-bold flex items-center justify-center shrink-0 select-none shadow-xs ${className}`}
      title={displayName}
      aria-label={displayName}
    >
      <span>{initial}</span>
    </div>
  )
}
