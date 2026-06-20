export default function ErrorMessage({ message = 'Something went wrong. Please try again.' }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-3">
      <div className="text-4xl">⚠️</div>
      <p className="text-red-600 font-medium">{message}</p>
    </div>
  )
}
