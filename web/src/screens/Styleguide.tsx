/**
 * /styleguide — design tokens + core components reference.
 * Shows the intentional visual identity, not a Bootstrap default.
 */
import { Card, CardHeader, CardBody, Button, Badge, DefinitionRow, SectionHeading } from '../design/primitives';
import { Verdict, MutationRefused, ChainVerifyBadge, Hash, Money, StatePill } from '../components/TrustComponents';
import { ALL_FAILURE_CODES, failureCodeMeta } from '../lib/failure-codes';

export function Styleguide() {
  return (
    <div className="max-w-3xl space-y-6 pb-12">
      <SectionHeading
        eyebrow="Design system"
        title="Styleguide"
        description="The intentional visual identity: a precision instrument. Calm, serious, legible."
      />

      {/* Verdicts */}
      <Card>
        <CardHeader><SectionHeading title="Verdicts" /></CardHeader>
        <CardBody>
          <div className="flex gap-4 flex-wrap">
            <Verdict decision="allow" />
            <Verdict decision="deny" failureCode="ACTION_MISMATCH" />
            <Verdict decision="approval_required" />
          </div>
        </CardBody>
      </Card>

      {/* Mutation refused */}
      <Card>
        <CardHeader><SectionHeading title="Mutation refused" /></CardHeader>
        <CardBody>
          <MutationRefused
            authorisedAmountMinor={2000}
            attemptedAmountMinor={9999900}
            currency="USD"
            failureCode="ACTION_MISMATCH"
          />
        </CardBody>
      </Card>

      {/* Chain verify */}
      <Card>
        <CardHeader><SectionHeading title="Chain verification" /></CardHeader>
        <CardBody>
          <div className="flex gap-3 items-center flex-wrap">
            <ChainVerifyBadge status="verified" />
            <ChainVerifyBadge status="broken" />
            <ChainVerifyBadge status="unknown" />
          </div>
        </CardBody>
      </Card>

      {/* Buttons */}
      <Card>
        <CardHeader><SectionHeading title="Buttons" /></CardHeader>
        <CardBody>
          <div className="flex gap-2 flex-wrap items-center">
            <Button variant="primary" size="sm">Primary</Button>
            <Button variant="secondary" size="sm">Secondary</Button>
            <Button variant="ghost" size="sm">Ghost</Button>
            <Button variant="danger" size="sm">Danger</Button>
            <Button variant="allow" size="sm">Allow</Button>
          </div>
        </CardBody>
      </Card>

      {/* Badges */}
      <Card>
        <CardHeader><SectionHeading title="Badges" /></CardHeader>
        <CardBody>
          <div className="flex gap-2 flex-wrap">
            <Badge tone="neutral">neutral</Badge>
            <Badge tone="allow">allow</Badge>
            <Badge tone="deny">deny</Badge>
            <Badge tone="pending">pending</Badge>
            <Badge tone="accent">accent</Badge>
            <Badge tone="muted">muted</Badge>
          </div>
        </CardBody>
      </Card>

      {/* State pills */}
      <Card>
        <CardHeader><SectionHeading title="State pills" /></CardHeader>
        <CardBody>
          <div className="flex gap-2 flex-wrap">
            <StatePill state="allow" />
            <StatePill state="deny" />
            <StatePill state="approval_required" />
            <StatePill state="pending" />
            <StatePill state="satisfied" />
            <StatePill state="rejected" />
            <StatePill state="not_required" />
          </div>
        </CardBody>
      </Card>

      {/* Money + hashes */}
      <Card>
        <CardHeader><SectionHeading title="Money and hashes" /></CardHeader>
        <CardBody>
          <dl>
            <DefinitionRow label="Money (USD)" mono>
              <Money minor={500} currency="USD" />
            </DefinitionRow>
            <DefinitionRow label="Money (GBP)" mono>
              <Money minor={2000} currency="GBP" />
            </DefinitionRow>
            <DefinitionRow label="Money (JPY)" mono>
              <Money minor={100000} currency="JPY" />
            </DefinitionRow>
            <DefinitionRow label="Hash" mono>
              <Hash value="sha256:a3f1c8d9e2b47065893f12da4567890bcdef0123456789abcdef0123456789ab" />
            </DefinitionRow>
          </dl>
        </CardBody>
      </Card>

      {/* Failure codes */}
      <Card>
        <CardHeader><SectionHeading title="Failure code glossary" /></CardHeader>
        <CardBody className="!p-0">
          <dl>
            {ALL_FAILURE_CODES.map((code) => {
              const meta = failureCodeMeta(code);
              return (
                <DefinitionRow key={code} label={code} mono>
                  <span className="text-sm">{meta.gloss}</span>
                </DefinitionRow>
              );
            })}
          </dl>
        </CardBody>
      </Card>
    </div>
  );
}
