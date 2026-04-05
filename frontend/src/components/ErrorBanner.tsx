interface Props {
  message: string;
}

export default function ErrorBanner({ message }: Props) {
  return (
    <div className="error-banner" role="alert">
      {message}
    </div>
  );
}
