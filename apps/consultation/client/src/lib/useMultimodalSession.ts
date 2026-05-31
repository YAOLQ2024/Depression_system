import { useCallback, useEffect, useRef, useState } from "react";

import { warmupMultimodalSession } from "../services/api/multimodal.api";

type UseMultimodalSessionOptions = {
	linkedSessionId?: string | null;
	resolveSessionId?: () => Promise<string | null>;
	missingSessionMessage: string;
	warmupModalities?: string[];
};

type UseMultimodalSessionResult = {
	multimodalSessionId: string | null;
	setMultimodalSessionId: (sessionId: string | null) => void;
	ensureSession: () => Promise<string>;
	clearSession: () => void;
};

const DEFAULT_MODALITIES = ["text", "audio", "face", "pose"];

export function useMultimodalSession({
	linkedSessionId = null,
	resolveSessionId,
	missingSessionMessage,
	warmupModalities = DEFAULT_MODALITIES,
}: UseMultimodalSessionOptions): UseMultimodalSessionResult {
	const [multimodalSessionId, setMultimodalSessionId] = useState<string | null>(linkedSessionId);
	const warmedUpSessionIdsRef = useRef<Set<string>>(new Set());

	const warmupSession = useCallback(
		async (sessionId: string) => {
			if (!sessionId || warmedUpSessionIdsRef.current.has(sessionId)) {
				return;
			}
			warmedUpSessionIdsRef.current.add(sessionId);
			try {
				await warmupMultimodalSession(sessionId, { modalities: warmupModalities });
			} catch {
				warmedUpSessionIdsRef.current.delete(sessionId);
			}
		},
		[warmupModalities],
	);

	useEffect(() => {
		if (linkedSessionId) {
			setMultimodalSessionId(linkedSessionId);
		}
	}, [linkedSessionId]);

	useEffect(() => {
		const activeSessionId = multimodalSessionId || linkedSessionId;
		if (!activeSessionId) {
			return;
		}
		void warmupSession(activeSessionId);
	}, [linkedSessionId, multimodalSessionId, warmupSession]);

	const ensureSession = useCallback(async () => {
		const activeSessionId = multimodalSessionId || linkedSessionId;
		if (activeSessionId) {
			if (multimodalSessionId !== activeSessionId) {
				setMultimodalSessionId(activeSessionId);
			}
			await warmupSession(activeSessionId);
			return activeSessionId;
		}

		if (resolveSessionId) {
			const resolvedSessionId = await resolveSessionId();
			if (resolvedSessionId) {
				setMultimodalSessionId(resolvedSessionId);
				await warmupSession(resolvedSessionId);
				return resolvedSessionId;
			}
		}

		throw new Error(missingSessionMessage);
	}, [
		linkedSessionId,
		missingSessionMessage,
		multimodalSessionId,
		resolveSessionId,
		warmupSession,
	]);

	const clearSession = useCallback(() => {
		setMultimodalSessionId(null);
	}, []);

	return {
		multimodalSessionId,
		setMultimodalSessionId,
		ensureSession,
		clearSession,
	};
}
