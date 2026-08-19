type PresentationBackdropProps = {
  variant?: 'public' | 'mission-control';
};

export function PresentationBackdrop({
  variant = 'public',
}: PresentationBackdropProps) {
  const isPublic = variant === 'public';

  return (
    <div
      aria-hidden="true"
      className={`presentation-backdrop ${
        isPublic ? 'presentation-backdrop--public' : 'presentation-backdrop--mission'
      }`}
    >
      <div className="presentation-backdrop__stars presentation-backdrop__stars--near" />
      <div className="presentation-backdrop__stars presentation-backdrop__stars--far" />
      {isPublic && (
        <>
          <div className="presentation-backdrop__deep-space" />
          <div className="presentation-backdrop__planet-field" />
          <div className="presentation-backdrop__constellation presentation-backdrop__constellation--alpha" />
          <div className="presentation-backdrop__constellation presentation-backdrop__constellation--beta" />
          <div className="presentation-backdrop__constellation presentation-backdrop__constellation--gamma" />
          <div className="presentation-backdrop__constellation presentation-backdrop__constellation--delta" />
          <div className="presentation-backdrop__orbit-cluster">
            <div className="presentation-backdrop__orbit presentation-backdrop__orbit--outer" />
            <div className="presentation-backdrop__orbit presentation-backdrop__orbit--mid" />
            <div className="presentation-backdrop__orbit presentation-backdrop__orbit--inner" />
            <div className="presentation-backdrop__planet presentation-backdrop__planet--violet" />
            <div className="presentation-backdrop__planet presentation-backdrop__planet--cyan" />
            <div className="presentation-backdrop__planet presentation-backdrop__planet--ice" />
            <div className="presentation-backdrop__planet presentation-backdrop__planet--ember" />
          </div>
          <div className="presentation-backdrop__orbit-cluster presentation-backdrop__orbit-cluster--lower">
            <div className="presentation-backdrop__orbit presentation-backdrop__orbit--outer" />
            <div className="presentation-backdrop__orbit presentation-backdrop__orbit--mid" />
            <div className="presentation-backdrop__orbit presentation-backdrop__orbit--inner" />
            <div className="presentation-backdrop__planet presentation-backdrop__planet--violet" />
            <div className="presentation-backdrop__planet presentation-backdrop__planet--cyan" />
            <div className="presentation-backdrop__planet presentation-backdrop__planet--ice" />
            <div className="presentation-backdrop__planet presentation-backdrop__planet--ember" />
          </div>
          <div className="presentation-backdrop__solar-system">
            <div className="presentation-backdrop__solar-star" />
            <div className="presentation-backdrop__solar-ring presentation-backdrop__solar-ring--one" />
            <div className="presentation-backdrop__solar-ring presentation-backdrop__solar-ring--two" />
            <div className="presentation-backdrop__solar-ring presentation-backdrop__solar-ring--three" />
            <div className="presentation-backdrop__solar-planet presentation-backdrop__solar-planet--one" />
            <div className="presentation-backdrop__solar-planet presentation-backdrop__solar-planet--two" />
            <div className="presentation-backdrop__solar-planet presentation-backdrop__solar-planet--three" />
          </div>
          <div className="presentation-backdrop__solar-system presentation-backdrop__solar-system--mid">
            <div className="presentation-backdrop__solar-star" />
            <div className="presentation-backdrop__solar-ring presentation-backdrop__solar-ring--one" />
            <div className="presentation-backdrop__solar-ring presentation-backdrop__solar-ring--two" />
            <div className="presentation-backdrop__solar-ring presentation-backdrop__solar-ring--three" />
            <div className="presentation-backdrop__solar-planet presentation-backdrop__solar-planet--one" />
            <div className="presentation-backdrop__solar-planet presentation-backdrop__solar-planet--two" />
            <div className="presentation-backdrop__solar-planet presentation-backdrop__solar-planet--three" />
          </div>
        </>
      )}
      <div className="presentation-backdrop__grid" />
      <div className="presentation-backdrop__glow presentation-backdrop__glow--violet" />
      <div className="presentation-backdrop__glow presentation-backdrop__glow--cyan" />
      <div className="presentation-backdrop__glow presentation-backdrop__glow--moon" />
      <div className="presentation-backdrop__horizon" />
    </div>
  );
}
